"""
Decision CLI — processes all classified transactions and makes recovery decisions.

Usage (from backend/):
    python -m scripts.run_decisions

Output:
    - Writes all results to the `decisions` table (idempotent — clears first)
    - Prints summary of auto-executed vs escalated per category
"""

import sys
import time
from collections import defaultdict

from app.core.database import SessionLocal
from app.models.models import Classification, Decision, RootCauseCategory
from app.services.decision_agent import decide_and_persist


def _print_summary(
    results: list[tuple[str, str, bool, float]],  # (category, action, auto_executed, conf)
    elapsed: float,
) -> None:
    total = len(results)
    if total == 0:
        print("[WARN] No results to summarise.")
        return

    auto_exec_count = sum(1 for _, _, auto, _ in results if auto)
    escalated_count = total - auto_exec_count

    # Per-category stats: category -> {"auto": int, "esc": int}
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"auto": 0, "esc": 0})
    for cat, action, auto, conf in results:
        if auto:
            by_cat[cat]["auto"] += 1
        else:
            by_cat[cat]["esc"] += 1

    print("\n" + "=" * 60)
    print("  Recovr — Decision Summary")
    print("=" * 60)
    print(f"  Total decisions : {total}")
    print(f"  Auto-executed   : {auto_exec_count} ({auto_exec_count/total*100:.1f}%)")
    print(f"  Escalated       : {escalated_count}  ({escalated_count/total*100:.1f}%)")
    print(f"  Elapsed         : {elapsed:.1f}s")

    print(f"\n  {'Category':<26} {'Auto':>6} {'Escalated':>10}")
    print("  " + "-" * 44)

    all_cats = list(RootCauseCategory)
    # Add 'other' manually for degraded cases
    cat_keys = [c.value for c in all_cats]
    if "other" not in cat_keys:
        cat_keys.append("other")

    for cat_val in cat_keys:
        stats = by_cat.get(cat_val)
        if not stats:
            continue
        print(f"  {cat_val:<26} {stats['auto']:>6} {stats['esc']:>10}")

    print("=" * 60)


def run() -> None:
    session = SessionLocal()
    try:
        # -- Idempotent: clear existing decisions
        deleted = session.query(Decision).delete()
        session.commit()
        if deleted:
            print(f"[INFO] Cleared {deleted} existing decision(s).")

        # -- Load classifications
        classifications = session.query(Classification).order_by(Classification.id).all()
        if not classifications:
            print("[WARN] No classifications found. Run run_classifier first.")
            return

        print(f"[INFO] Making decisions for {len(classifications)} transactions...\n")

        start = time.time()
        results = []

        for clf in classifications:
            tx = clf.transaction
            decision = decide_and_persist(tx, clf, session)

            status_str = "[AUTO]" if decision.auto_executed else "[ESC] "
            print(
                f"  {status_str} tx#{tx.id:>4} | {clf.root_cause_category.value:<22} "
                f"-> {decision.action_type.value:<20} (conf={decision.confidence:.2f})"
            )

            results.append((
                clf.root_cause_category.value,
                decision.action_type.value,
                decision.auto_executed,
                decision.confidence,
            ))

        session.commit()
        elapsed = time.time() - start
        print(f"\n[OK] Committed {len(results)} decisions in {elapsed:.1f}s.")

        _print_summary(results, elapsed)

    except Exception as exc:
        session.rollback()
        print(f"[FAIL] Decision run failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    run()
