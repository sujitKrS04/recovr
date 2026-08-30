"""
Recovery Receipts for Recovr.

Generates a human-readable audit trail string for terminal transactions,
combining classification reasoning, decision reasoning, and final execution outcome.
"""

from sqlalchemy.orm import Session

from app.models.models import Decision, RecoveryReceipt, Transaction, TransactionStatus


def _format_money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.0f}"


def generate_receipt(tx: Transaction, session: Session) -> RecoveryReceipt | None:
    """
    Generate a RecoveryReceipt if the transaction is in a terminal state.
    """
    terminal_states = {
        TransactionStatus.recovered,
        TransactionStatus.failed,
        TransactionStatus.escalated,
        TransactionStatus.suppressed,
        TransactionStatus.exhausted,
    }
    
    if tx.status not in terminal_states:
        return None

    # Get the latest classification and decision
    # (Assuming 1-to-1 for this pipeline, but `.order_by` or `[-1]` is safer if 1-to-many)
    classification = tx.classifications[0] if tx.classifications else None
    decision = tx.decisions[0] if tx.decisions else None
    
    # 1. Classification part
    if classification:
        cat = classification.root_cause_category.value
        conf = classification.confidence * 100
        method = classification.classifier_method.value
        class_str = f"Classified as {cat} ({conf:.0f}% confidence, {method})."
    else:
        class_str = "No classification found."

    # 2. Decision part
    if decision:
        act = decision.action_type.value
        # Use reasoning if available
        if decision.reasoning:
            dec_str = f"Routed to {act}: {decision.reasoning}"
        else:
            auto = "auto-executed" if decision.auto_executed else "escalated"
            dec_str = f"Routed to {act} ({decision.confidence*100:.0f}% confidence, {auto})."
    else:
        dec_str = "No decision found."

    # 3. Outcome part
    if tx.status == TransactionStatus.recovered:
        out_str = f"Recovered {_format_money(tx.amount, tx.currency)} successfully."
    elif tx.status == TransactionStatus.suppressed:
        out_str = "Recovery suppressed due to compliance (DND) rules."
    elif tx.status == TransactionStatus.exhausted:
        out_str = f"Recovery exhausted after {tx.retry_count} failed attempts."
    elif tx.status == TransactionStatus.escalated:
        out_str = "Escalated to human review queue for manual intervention."
    else:
        out_str = f"Final state: {tx.status.value}."

    full_reasoning = f"{class_str} {dec_str} {out_str}"

    # Determine outcome enum value
    if tx.status == TransactionStatus.recovered:
        outcome_enum = "recovered"
    elif tx.status == TransactionStatus.suppressed:
        outcome_enum = "suppressed"
    elif tx.status == TransactionStatus.exhausted:
        outcome_enum = "failed"
    elif tx.status == TransactionStatus.escalated:
        outcome_enum = "escalated"
    else:
        outcome_enum = "failed"

    receipt = RecoveryReceipt(
        transaction_id=tx.id,
        root_cause=cat if classification else "unknown",
        action_taken=act if decision else "none",
        reasoning=full_reasoning,
        amount_recovered=tx.amount if tx.status == TransactionStatus.recovered else None,
        outcome=outcome_enum
    )
    session.add(receipt)
    return receipt
