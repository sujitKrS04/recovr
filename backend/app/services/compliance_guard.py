"""
Compliance Guard for Recovr.

Acts as a hard gate before any execution. Enforces safety rules, cooldowns,
retry limits, and defense-in-depth against fraud auto-execution.
"""

from datetime import datetime, timedelta, timezone

from app.models.models import ActionType, RootCauseCategory, Transaction, TransactionStatus


class ComplianceGuardBlocked(Exception):
    """Raised when an action violates a compliance or safety rule."""
    def __init__(self, message: str, force_status: TransactionStatus | None = None):
        super().__init__(message)
        self.message = message
        self.force_status = force_status


def enforce_compliance(tx: Transaction, action_type: ActionType, category: RootCauseCategory | None = None):
    """
    Checks all compliance rules. Raises ComplianceGuardBlocked if any rule is violated.
    """
    # 1. Defense in depth: Fraud can never be auto-contacted or auto-retried
    if category == RootCauseCategory.fraud_false_positive:
        if action_type != ActionType.escalate_human:
            raise ComplianceGuardBlocked(
                message=f"Fraud signal safety violation: Attempted {action_type.value} on fraud flag. Forced escalation.",
                force_status=TransactionStatus.escalated
            )

    # 2. DND Opt-Out: No contact-based actions
    if tx.dnd_opt_out:
        contact_actions = (ActionType.payment_link, ActionType.update_card_prompt)
        if action_type in contact_actions:
            raise ComplianceGuardBlocked(
                message=f"DND Violation: Customer opted out of contact. Blocked {action_type.value}.",
                force_status=TransactionStatus.suppressed
            )

    # 3. Max retries (hard limit = 3)
    # The retry_count reflects past failures. If they already failed 3 times, do not execute further.
    if tx.retry_count >= 3:
        raise ComplianceGuardBlocked(
            message=f"Retry limit exceeded: Transaction has already failed {tx.retry_count} times.",
            force_status=TransactionStatus.exhausted
        )

    # 4. Minimum 4-hour cooldown
    if tx.last_action_at:
        now = datetime.now(timezone.utc)
        # Ensure timezone-aware math
        last_action = tx.last_action_at
        if last_action.tzinfo is None:
            last_action = last_action.replace(tzinfo=timezone.utc)
        
        time_since_last = now - last_action
        if time_since_last < timedelta(hours=4):
            # Blocked by cooldown, keep status as is (recovering/escalated/etc.)
            raise ComplianceGuardBlocked(
                message=f"Cooldown active: Only {time_since_last.total_seconds() / 3600:.1f}h since last action (min 4h)."
            )

    # If we get here, all checks passed.
    return True
