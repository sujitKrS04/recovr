"""
Full Agent Pipeline Executer for Recovr.

Executes all automated decisions (via the action executors), updates transaction statuses,
and compares the agent's recovery performance against the naive baseline.
"""

import sys
import time

from app.core.database import SessionLocal
from app.models.models import ActionLog, BaselineResult, Decision, Transaction, RecoveryReceipt
from app.services.executors import execute_decision
from app.services.receipts import generate_receipt


def run() -> None:
    session = SessionLocal()
    try:
        # Idempotent: clear existing action logs and receipts
        deleted_receipts = session.query(RecoveryReceipt).delete()
        deleted_logs = session.query(ActionLog).delete()
        session.commit()
        if deleted_logs or deleted_receipts:
            print(f"[INFO] Cleared {deleted_logs} existing action log(s) and {deleted_receipts} receipt(s).")

        decisions = session.query(Decision).order_by(Decision.id).all()
        if not decisions:
            print("[WARN] No decisions found. Run run_decisions first.")
            return

        baseline_results = session.query(BaselineResult).all()
        if not baseline_results:
            print("[WARN] No baseline results found. Run run_baseline first for comparison.")
            return

        print(f"[INFO] Executing agent actions for {len(decisions)} decisions...\n")

        start = time.time()
        
        agent_recovered_count = 0
        agent_amount_recovered = 0.0
        
        for decision in decisions:
            tx = decision.transaction
            # Get category from the transaction's classification
            category = tx.classifications[0].root_cause_category if tx.classifications else None
            
            # Execute
            action_log = execute_decision(tx, decision, session, category=category)
            
            if action_log.success and action_log.amount_recovered:
                agent_recovered_count += 1
                agent_amount_recovered += float(action_log.amount_recovered)
                
            status_str = "[SUCCESS]" if action_log.success else "[FAILED] "
            if not decision.auto_executed:
                status_str = "[ESCALATED]"
                
            # If blocked by compliance, it will be marked FAILED with a BLOCKED message
            if action_log.error_message and "BLOCKED BY COMPLIANCE" in action_log.error_message:
                status_str = "[BLOCKED] "
                
            print(f"  {status_str:<11} tx#{tx.id:>4} | Action: {decision.action_type.value:<20}")
            
            # Generate Receipt
            generate_receipt(tx, session)

        session.commit()
        elapsed = time.time() - start

        # -- Compute Uplift vs Baseline --
        baseline_recovered_count = sum(1 for b in baseline_results if b.recovered)
        baseline_amount = sum(float(b.amount_recovered) for b in baseline_results if b.recovered)

        uplift_amount = agent_amount_recovered - baseline_amount
        uplift_pct = (uplift_amount / baseline_amount * 100) if baseline_amount else 0.0

        print("\n" + "=" * 60)
        print("  Recovr — Final Agent Performance")
        print("=" * 60)
        print(f"  Agent Recovered    : {agent_recovered_count} transactions")
        print(f"  Agent Revenue      : INR {agent_amount_recovered:,.0f}")
        print("-" * 60)
        print(f"  Baseline Recovered : {baseline_recovered_count} transactions")
        print(f"  Baseline Revenue   : INR {baseline_amount:,.0f}")
        print("-" * 60)
        print(f"  UPLIFT             : INR +{uplift_amount:,.0f} (+{uplift_pct:.1f}%)")
        print(f"  Elapsed            : {elapsed:.1f}s")
        print("=" * 60)

    except Exception as exc:
        session.rollback()
        print(f"[FAIL] Executor run failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    run()
