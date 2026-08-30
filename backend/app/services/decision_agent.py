"""
Decision agent service for Recovr.

Maps classified root causes to recovery actions with confidence gating.
Hard rule: 'fraud_false_positive' always escalates to human review, regardless of classifier confidence.
Confidence gating: >= 0.75 is auto-executed. Below 0.75 goes to human review.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.models import (
    ActionType,
    Classification,
    Decision,
    RootCauseCategory,
    Transaction,
)

logger = logging.getLogger(__name__)

AUTO_EXECUTE_THRESHOLD = 0.75


@dataclass
class DecisionResult:
    action_type: ActionType
    confidence: float
    auto_executed: bool
    reasoning: str


def make_decision(classification: Classification) -> DecisionResult:
    """
    Map root cause to an action, applying confidence gating and hard rules.
    """
    cat = classification.root_cause_category
    
    # 1. Hard rule for Fraud
    if cat == RootCauseCategory.fraud_false_positive:
        return DecisionResult(
            action_type=ActionType.escalate_human,
            confidence=0.10,
            auto_executed=False,
            reasoning="Fraud-adjacent signal (false positive), requires human judgment. Deliberately refusing to auto-execute."
        )

    # 2. Map standard categories to actions and baseline confidence
    # (In a real system, confidence might be a product of classifier conf * rule conf)
    if cat in (RootCauseCategory.gateway_timeout, RootCauseCategory.bank_downtime):
        base_action = ActionType.instant_retry
        base_conf = 0.90
        reason_template = "Clean signal for technical downtime ({cat}). Safe to auto-retry."
        
    elif cat == RootCauseCategory.insufficient_funds:
        base_action = ActionType.payment_link
        base_conf = 0.85
        reason_template = "Insufficient funds detected. Sending payment link to give customer time and a nudge."
        
    elif cat == RootCauseCategory.card_declined:
        base_action = ActionType.update_card_prompt
        base_conf = 0.70
        reason_template = "Card declined (potentially expired/blocked). Prompting customer to update card."
        
    elif cat == RootCauseCategory.otp_failure:
        base_action = ActionType.instant_retry
        base_conf = 0.70
        reason_template = "OTP failure detected. Suggesting instant retry with delay."
        
    else:
        # 'other' or unknown categories
        base_action = ActionType.escalate_human
        base_conf = 0.10
        reason_template = "Unrecognized or degraded classification. Escalate for safety."

    reason_str = reason_template.format(cat=cat.value)
    auto_execute = base_conf >= AUTO_EXECUTE_THRESHOLD

    if not auto_execute:
        # Append explanation of why it was gated
        reason_str += f" Confidence ({base_conf:.2f}) below threshold ({AUTO_EXECUTE_THRESHOLD:.2f}) -> Escalate to human review."

    return DecisionResult(
        action_type=base_action,
        confidence=base_conf,
        auto_executed=auto_execute,
        reasoning=reason_str
    )


def decide_and_persist(tx: Transaction, classification: Classification, session: Session) -> Decision:
    """
    Make a decision for a transaction and persist it to the DB.
    Does NOT commit.
    """
    result = make_decision(classification)
    
    decision = Decision(
        transaction_id=tx.id,
        action_type=result.action_type,
        confidence=result.confidence,
        auto_executed=result.auto_executed,
        reasoning=result.reasoning
    )
    session.add(decision)
    return decision
