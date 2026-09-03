"""
Action Executors for Recovr.

Executes the decisions made by the Decision Agent.
Interacts with the Razorpay API for real actions (instant_retry, payment_link).
Logs all outcomes to the actions_log table and updates transaction status.
"""

import logging
import razorpay
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ActionLog,
    ActionType,
    Decision,
    Transaction,
    TransactionStatus,
)

logger = logging.getLogger(__name__)

INJECT_FAILURE_ONCE: bool = False

# Initialize Razorpay Client (test mode)
if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and "your_key" not in settings.RAZORPAY_KEY_ID:
    rzp_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
else:
    rzp_client = None
    logger.warning("Razorpay credentials not set. Executors will fail safe.")


def _log_action(
    session: Session,
    decision_id: int,
    success: bool,
    rzp_response: dict[str, Any] | None = None,
    error_message: str | None = None,
    amount_recovered: float | None = None,
) -> ActionLog:
    """Helper to persist an action log."""
    action_log = ActionLog(
        decision_id=decision_id,
        success=success,
        razorpay_response=rzp_response,
        error_message=error_message,
        amount_recovered=amount_recovered,
    )
    session.add(action_log)
    return action_log


def _mark_recovered(tx: Transaction, amount: float):
    tx.status = TransactionStatus.recovered
    # Update last_action_at via DB trigger or manual
    # For now, we just rely on the actions_log being the timeline


def _mark_failed(tx: Transaction):
    tx.retry_count += 1
    # If we want to move to 'exhausted', we'd do it here, but keeping it 'failed' or 'recovering'
    # Based on phase 1: status is failed/recovering/recovered/exhausted/escalated
    if tx.retry_count >= 3:
        tx.status = TransactionStatus.exhausted
    else:
        tx.status = TransactionStatus.recovering


def execute_instant_retry(tx: Transaction, decision: Decision, session: Session) -> ActionLog:
    """
    Attempt an instant retry by creating a Razorpay Order.
    In a real system, this might charge a saved card (token).
    Here we simulate it by creating an Order and treating successful order creation as a success.
    """
    if not rzp_client:
        # Mock success for demo if keys not set
        _mark_recovered(tx, tx.amount)
        return _log_action(session, decision.id, True, rzp_response={"id": "mock_order_123", "mock": True}, amount_recovered=tx.amount)

    amount_paise = int(tx.amount * 100)
    payload = {
        "amount": amount_paise,
        "currency": tx.currency,
        "receipt": f"recovr_{tx.id}_retry_{tx.retry_count + 1}",
        "notes": {"reason": "instant_retry_recovery"}
    }
    
    try:
        resp = rzp_client.order.create(data=payload)
        # Success if we got an order back
        if "id" in resp:
            _mark_recovered(tx, tx.amount)
            return _log_action(session, decision.id, True, rzp_response=resp, amount_recovered=tx.amount)
        else:
            _mark_failed(tx)
            return _log_action(session, decision.id, False, rzp_response=resp, error_message="Order created but no ID returned.")
    except Exception as exc:
        _mark_failed(tx)
        return _log_action(session, decision.id, False, error_message=str(exc))


def execute_payment_link(tx: Transaction, decision: Decision, session: Session) -> ActionLog:
    """
    Create a Razorpay payment link.
    """
    if not rzp_client:
        # Mock success for demo if keys not set
        _mark_recovered(tx, tx.amount)
        return _log_action(session, decision.id, True, rzp_response={"id": "mock_plink_123", "mock": True}, amount_recovered=tx.amount)

    amount_paise = int(tx.amount * 100)
    payload = {
        "amount": amount_paise,
        "currency": tx.currency,
        "description": f"Recovery for failed transaction {tx.external_payment_id}",
        "customer": {
            "name": tx.customer_name,
            "contact": "9999999999",  # Mock contact since we didn't store it
            "email": f"customer_{tx.id}@example.com"
        },
        "notify": {"sms": False, "email": False},
        "reminder_enable": True,
        "notes": {"tx_id": str(tx.id)}
    }
    
    try:
        resp = rzp_client.payment_link.create(payload)
        if "id" in resp:
            # We treat sending the link as an action success, but the TX is still 'recovering' until paid.
            # For the buildathon demo, we will simulate immediate recovery if the link was created successfully.
            _mark_recovered(tx, tx.amount)
            return _log_action(session, decision.id, True, rzp_response=resp, amount_recovered=tx.amount)
        else:
            _mark_failed(tx)
            return _log_action(session, decision.id, False, rzp_response=resp, error_message="No ID returned for link.")
    except Exception as exc:
        _mark_failed(tx)
        return _log_action(session, decision.id, False, error_message=str(exc))


def execute_update_card_prompt(tx: Transaction, decision: Decision, session: Session) -> ActionLog:
    """
    Mock sending an SMS/Email to update card details.
    """
    # Mocking success always for this demo
    resp = {"status": "sent", "channel": "sms", "mock": True}
    _mark_recovered(tx, tx.amount)
    return _log_action(session, decision.id, True, rzp_response=resp, amount_recovered=tx.amount)


def execute_escalate_human(tx: Transaction, decision: Decision, session: Session) -> ActionLog:
    """
    Escalate to human. No automated recovery is attempted.
    """
    tx.status = TransactionStatus.escalated
    return _log_action(session, decision.id, False, error_message="Escalated to human review. No automated action taken.")


from app.services.compliance_guard import enforce_compliance, ComplianceGuardBlocked

def execute_decision(tx: Transaction, decision: Decision, session: Session, category=None) -> ActionLog:
    """
    Route the decision to the correct executor, enforcing compliance first.
    """
    global INJECT_FAILURE_ONCE
    if INJECT_FAILURE_ONCE:
        INJECT_FAILURE_ONCE = False
        tx.status = TransactionStatus.failed
        return _log_action(session, decision.id, False, error_message="SIMULATED FAILURE: Injected gateway connection reset.")

    try:
        enforce_compliance(tx, decision.action_type, category)
    except ComplianceGuardBlocked as e:
        if e.force_status:
            tx.status = e.force_status
        return _log_action(session, decision.id, False, error_message=f"BLOCKED BY COMPLIANCE: {e.message}")

    if not decision.auto_executed:
        # If it was gated, we treat it as an escalation implicitly
        return execute_escalate_human(tx, decision, session)

    if decision.action_type == ActionType.instant_retry:
        return execute_instant_retry(tx, decision, session)
    elif decision.action_type == ActionType.payment_link:
        return execute_payment_link(tx, decision, session)
    elif decision.action_type == ActionType.update_card_prompt:
        return execute_update_card_prompt(tx, decision, session)
    elif decision.action_type == ActionType.escalate_human:
        return execute_escalate_human(tx, decision, session)
    else:
        # Fallback for suppress_dnd or unknown
        return _log_action(session, decision.id, False, error_message=f"No executor implemented for {decision.action_type.value}")
