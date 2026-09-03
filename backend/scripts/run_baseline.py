"""
Baseline comparator CLI for Recovr.

Simulates a 'naive' recovery approach: blind instant retry on every failed transaction,
with no classification, no gating, and no human review.
"""

import sys
import time

from app.core.database import SessionLocal
from app.models.models import BaselineResult, Transaction
from app.services.executors import execute_instant_retry, Decision, ActionType


def run() -> None:
    session = SessionLocal()
    try:
        # Idempotent: clear existing baseline results
        deleted = session.query(BaselineResult).delete()
        session.commit()
        if deleted:
            print(f"[INFO] Cleared {deleted} existing baseline result(s).")

        transactions = session.query(Transaction).order_by(Transaction.id).all()
        if not transactions:
            print("[WARN] No transactions found. Run generate_batch first.")
            return

        print(f"[INFO] Running naive baseline (blind instant retry) on {len(transactions)} transactions...\n")

        start = time.time()
        results = []
        recovered_count = 0
        amount_recovered = 0.0

        for tx in transactions:
            
            # In test mode, Razorpay order.create always succeeds. 
            # In reality, blindly retrying an 'insufficient_funds' or 'fraud' would FAIL.
            # To simulate realistic baseline uplift for the demo, we mock the real-world 
            # behaviour where only technical issues (gateway/bank) succeed on blind instant retry.
            
            reason = tx.failure_reason.lower()
            will_succeed = any(x in reason for x in ["gateway", "timeout", "bank", "sla"])
                
            is_recovered = False
            if will_succeed:
                # We simulate an instant retry order creation
                import razorpay
                from app.core.config import settings
                if settings.RAZORPAY_KEY_ID and "your_key" not in settings.RAZORPAY_KEY_ID:
                    try:
                        rzp_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                        order_api = getattr(rzp_client, "order")
                        resp = order_api.create({
                            "amount": int(tx.amount * 100),
                            "currency": tx.currency,
                            "receipt": f"baseline_{tx.id}"
                        })
                        if "id" in resp:
                            is_recovered = True
                    except Exception:
                        pass
                else:
                    # Mock success if Razorpay isn't configured
                    is_recovered = True

            if is_recovered:
                recovered_count += 1
                amount_recovered += float(tx.amount)

            baseline = BaselineResult(
                transaction_id=tx.id,
                recovered=is_recovered,
                amount_recovered=tx.amount if is_recovered else 0.0
            )
            session.add(baseline)
            results.append(baseline)

        session.commit()
        elapsed = time.time() - start

        print("\n" + "=" * 60)
        print("  Recovr — Baseline Comparator")
        print("=" * 60)
        print(f"  Total transactions : {len(transactions)}")
        print(f"  Recovered          : {recovered_count} ({recovered_count/len(transactions)*100:.1f}%)")
        print(f"  Amount Recovered   : INR {amount_recovered:,.0f}")
        print(f"  Elapsed            : {elapsed:.1f}s")
        print("=" * 60)

    except Exception as exc:
        session.rollback()
        print(f"[FAIL] Baseline run failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    run()
