"""
Recovr SQLAlchemy models — all 6 tables for Phase 1 + multi-tenant org_id.
"""
from datetime import datetime
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
# Import auth models so Alembic sees them in Base.metadata
import app.models.auth_models  # noqa: F401


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransactionStatus(str, enum.Enum):
    failed = "failed"
    recovering = "recovering"
    recovered = "recovered"
    exhausted = "exhausted"
    escalated = "escalated"
    suppressed = "suppressed"


class RootCauseCategory(str, enum.Enum):
    card_declined = "card_declined"
    insufficient_funds = "insufficient_funds"
    gateway_timeout = "gateway_timeout"
    bank_downtime = "bank_downtime"
    otp_failure = "otp_failure"
    fraud_false_positive = "fraud_false_positive"
    other = "other"


class ClassifierMethod(str, enum.Enum):
    rule = "rule"
    llm = "llm"


class ActionType(str, enum.Enum):
    instant_retry = "instant_retry"
    payment_link = "payment_link"
    update_card_prompt = "update_card_prompt"
    escalate_human = "escalate_human"
    suppress_dnd = "suppress_dnd"


class RecoveryOutcome(str, enum.Enum):
    recovered = "recovered"
    failed = "failed"
    escalated = "escalated"
    suppressed = "suppressed"


# ---------------------------------------------------------------------------
# 1. transactions
# ---------------------------------------------------------------------------

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # org_id — nullable so existing rows survive until re-seeded
    org_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    external_payment_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(256), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    failure_reason: Mapped[str] = mapped_column(Text, nullable=True)
    gateway: Mapped[str] = mapped_column(String(64), nullable=True)
    bank: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"),
        nullable=False,
        default=TransactionStatus.failed,
        index=True,
    )
    dnd_opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    classifications: Mapped[list["Classification"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    receipt: Mapped["RecoveryReceipt | None"] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    baseline_result: Mapped["BaselineResult | None"] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transactions_status_created_at", "status", "created_at"),
    )


# ---------------------------------------------------------------------------
# 2. classifications
# ---------------------------------------------------------------------------

class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    root_cause_category: Mapped[RootCauseCategory] = mapped_column(
        Enum(RootCauseCategory, name="root_cause_category"), nullable=False
    )
    classifier_method: Mapped[ClassifierMethod] = mapped_column(
        Enum(ClassifierMethod, name="classifier_method"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="classifications")


# ---------------------------------------------------------------------------
# 3. decisions
# ---------------------------------------------------------------------------

class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    auto_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="decisions")
    actions_log: Mapped[list["ActionLog"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 4. actions_log
# ---------------------------------------------------------------------------

class ActionLog(Base):
    __tablename__ = "actions_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    razorpay_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_recovered: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Relationships
    decision: Mapped["Decision"] = relationship(back_populates="actions_log")


# ---------------------------------------------------------------------------
# 5. recovery_receipts
# ---------------------------------------------------------------------------

class RecoveryReceipt(Base):
    __tablename__ = "recovery_receipts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    cost_of_intervention: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_recovered: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    outcome: Mapped[RecoveryOutcome] = mapped_column(
        Enum(RecoveryOutcome, name="recovery_outcome"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="receipt")


# ---------------------------------------------------------------------------
# 6. baseline_results
# ---------------------------------------------------------------------------

class BaselineResult(Base):
    __tablename__ = "baseline_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    amount_recovered: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="baseline_result")
