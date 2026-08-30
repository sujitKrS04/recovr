"""
Classifier CLI — processes the full transaction batch and writes classifications.

Usage (from backend/):
    python -m scripts.run_classifier

Options (env-based):
    OPENROUTER_API_KEY  — if set, LLM fallback is live; otherwise degraded mode

Output:
    - Writes all results to the `classifications` table (idempotent — clears first)
    - Prints a summary table: rule vs LLM split, avg confidence per category
    - Prints cache hit stats
"""

import sys
import time
from collections import defaultdict

from app.core.database import SessionLocal
from app.models.models import Classification, RootCauseCategory, Transaction
from app.services.classifier import (
    classify_and_persist,
    get_cache_stats,
)


def _print_summary(
    results: list[tuple[str, str, float]],  # (category, method, confidence)
    elapsed: float,
) -> None:
    total = len(results)
    if total == 0:
        print("[WARN] No results to summarise.")
        return

    rule_results = [(c, conf) for c, m, conf in results if m == "rule"]
    llm_results  = [(c, conf) for c, m, conf in results if m == "llm"]

    # Per-category stats
    by_cat: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for cat, method, conf in results:
        by_cat[cat].append((method, conf))

    target_counts = {
        "card_declined": 36,
        "insufficient_funds": 24,
        "gateway_timeout": 24,
        "bank_downtime": 18,
        "otp_failure": 12,
        "fraud_false_positive": 6,
        "other": 0,
    }

    print("\n" + "=" * 76)
    print("  Recovr — Classification Summary")
    print("=" * 76)
    print(f"  Total classified : {total}")
    print(f"  Rule-based       : {len(rule_results)} ({len(rule_results)/total*100:.1f}%)")
    print(f"  LLM (OpenRouter) : {len(llm_results)}  ({len(llm_results)/total*100:.1f}%)")
    print(f"  Elapsed          : {elapsed:.1f}s")

    cache = get_cache_stats()
    print(f"  LLM cache hits   : {cache['cache_hits']} ({cache['cached_entries']} unique cached)")

    print(f"\n  {'Category':<26} {'Count':>5} {'Target':>6} {'Rule':>5} {'LLM':>5} {'Avg Conf':>9}")
    print("  " + "-" * 58)

    all_cats = list(RootCauseCategory)
    for cat in all_cats:
        rows = by_cat.get(cat.value, [])
        if not rows and target_counts.get(cat.value, 0) == 0:
            continue
        n = len(rows)
        n_rule = sum(1 for m, _ in rows if m == "rule")
        n_llm  = sum(1 for m, _ in rows if m == "llm")
        avg_conf = sum(c for _, c in rows) / n if n else 0.0
        target_n = target_counts.get(cat.value, "?")
        ok = "[OK]" if n == target_n else "[!!]"
        print(
            f"  {cat.value:<26} {n:>5} {str(target_n):>6} {n_rule:>5} {n_llm:>5} {avg_conf:>8.3f}  {ok}"
        )

    if rule_results:
        avg_rule_conf = sum(c for _, c in rule_results) / len(rule_results)
        print(f"\n  Rule avg confidence : {avg_rule_conf:.3f}")
    if llm_results:
        avg_llm_conf = sum(c for _, c in llm_results) / len(llm_results)
        print(f"  LLM  avg confidence : {avg_llm_conf:.3f}")

    print("=" * 76)


def run() -> None:
    session = SessionLocal()
    try:
        # -- Idempotent: clear existing classifications
        deleted = session.query(Classification).delete()
        session.commit()
        if deleted:
            print(f"[INFO] Cleared {deleted} existing classification(s).")

        # -- Load all transactions
        transactions = session.query(Transaction).order_by(Transaction.id).all()
        if not transactions:
            print("[WARN] No transactions found. Run generate_batch first.")
            return

        print(f"[INFO] Classifying {len(transactions)} transactions...")
        print("       (rule-based first, LLM fallback for unmatched cases)\n")

        start = time.time()
        results: list[tuple[str, str, float]] = []
        llm_count = 0

        for i, tx in enumerate(transactions, 1):
            clf = classify_and_persist(tx, session)

            method_label = clf.classifier_method.value
            if method_label == "llm":
                llm_count += 1
                print(
                    f"  [LLM] tx#{tx.id:>4} | {tx.failure_reason[:55]:<55} "
                    f"-> {clf.root_cause_category.value} (conf={clf.confidence:.2f})"
                )
            else:
                # Print every 20th rule result to avoid spam
                if i % 20 == 0:
                    print(
                        f"  [RULE x{i:>3}] latest: {tx.failure_reason[:45]:<45} "
                        f"-> {clf.root_cause_category.value}"
                    )

            results.append((
                clf.root_cause_category.value,
                method_label,
                clf.confidence,
            ))

            # Small sleep after each LLM call to respect rate limits
            if method_label == "llm":
                time.sleep(3.5)

        session.commit()
        elapsed = time.time() - start
        print(f"\n[OK] Committed {len(results)} classifications in {elapsed:.1f}s.")

        _print_summary(results, elapsed)

    except Exception as exc:
        session.rollback()
        print(f"[FAIL] Classifier run failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    run()
