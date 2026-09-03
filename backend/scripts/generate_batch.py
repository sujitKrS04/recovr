"""
Synthetic failed-payment batch generator for Recovr.

Usage (from backend/):
    python -m scripts.generate_batch

Behaviour:
    - Clears all existing rows in `transactions` (and cascades to child tables)
    - Seeds 120 realistic failed Indian payment records
    - Prints a summary distribution table

Failure categories and target ratios:
    card_declined        30%  (36)
    insufficient_funds   20%  (24)
    gateway_timeout      20%  (24)
    bank_downtime        15%  (18)
    otp_failure          10%  (12)
    fraud_false_positive  5%  ( 6)
    Total                     120
"""

import random
import sys
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.models import (
    RootCauseCategory,
    Transaction,
    TransactionStatus,
)

# ---------------------------------------------------------------------------
# Seed for reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

fake = Faker("en_IN")
fake.seed_instance(SEED)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOTAL = 120
DND_RATE = 0.08  # ~8% of records opt out of outreach

BANKS = [
    "HDFC Bank",
    "ICICI Bank",
    "State Bank of India",
    "Axis Bank",
    "Kotak Mahindra Bank",
    "Punjab National Bank",
    "Bank of Baroda",
    "Yes Bank",
    "IndusInd Bank",
    "IDFC First Bank",
]

BANK_WEIGHTS = [25, 22, 20, 15, 10, 3, 2, 1, 1, 1]  # realistic market-share proxy

GATEWAYS = ["razorpay", "razorpay", "razorpay", "paytm", "cashfree"]  # 60% Razorpay

# ---------------------------------------------------------------------------
# Category config: (enum_value, weight, failure_reasons[], typical_amounts_range)
# ---------------------------------------------------------------------------
CATEGORIES = [
    {
        "category": RootCauseCategory.card_declined,
        "count": 36,  # 30%
        "reasons": [
            "Card declined - Insufficient credit limit",
            "Card declined - Expired card",
            "Card declined - Card blocked by issuer",
            "Card declined - Do not honour",
            "Card declined - Card reported stolen",
            "Card declined - Card not set up for recurring payments",
        ],
        "amount_profile": "medium",  # ₹500–₹15,000
    },
    {
        "category": RootCauseCategory.insufficient_funds,
        "count": 24,  # 20%
        "reasons": [
            "Insufficient funds in account",
            "Insufficient balance - debit failed",
            "Debit failed - insufficient balance",
        ],
        "amount_profile": "small",  # ₹200–5,000
    },
    {
        "category": RootCauseCategory.gateway_timeout,
        "count": 24,  # 20%
        "reasons": [
            "Payment gateway request timed out",
            "Connection to payment processor lost",
            "Gateway timeout after 30s",
            "Upstream payment provider unreachable",
            "Network timeout during payment processing",
        ],
        "amount_profile": "any",
    },
    {
        "category": RootCauseCategory.bank_downtime,
        "count": 18,  # 15%
        "reasons": [
            "Issuing bank server unavailable",
            "Bank undergoing scheduled maintenance",
            "Core banking system temporarily down",
            "Bank not responding within SLA window",
        ],
        "amount_profile": "any",
    },
    {
        "category": RootCauseCategory.otp_failure,
        "count": 12,  # 10%
        "reasons": [
            "OTP verification failed - incorrect OTP entered",
            "OTP expired before submission",
            "3D Secure authentication failed",
            "OTP not received by customer",
        ],
        "amount_profile": "medium",
    },
    {
        "category": RootCauseCategory.fraud_false_positive,
        "count": 6,  # 5%
        "reasons": [
            "Transaction flagged by automated fraud detection",
            "Risk engine declined - unusual spending pattern",
            "Velocity check triggered - multiple attempts",
            "Suspicious activity flag from issuer's risk system",
        ],
        "amount_profile": "large",  # ₹8,000–₹45,000 — fraud rules trigger on large amounts
    },
]


# ---------------------------------------------------------------------------
# Amount generator by profile
# ---------------------------------------------------------------------------

def _amount(profile: str) -> float:
    """Return a realistic transaction amount (rounded to nearest ₹) for a given profile."""
    if profile == "small":
        # ₹200–₹5,000, heavy weight toward ₹500–₹2,000
        raw = random.lognormvariate(6.5, 0.6)  # mean ~₹665
        return round(max(200, min(5000, raw)), 0)
    elif profile == "medium":
        # ₹500–₹15,000
        raw = random.lognormvariate(7.5, 0.7)  # mean ~₹1,800
        return round(max(500, min(15000, raw)), 0)
    elif profile == "large":
        # ₹8,000–₹45,000
        raw = random.lognormvariate(9.5, 0.5)  # mean ~₹13,360
        return round(max(8000, min(45000, raw)), 0)
    else:  # "any"
        # ₹200–₹45,000 with log-normal skew toward lower values
        raw = random.lognormvariate(7.8, 1.0)
        return round(max(200, min(45000, raw)), 0)


# ---------------------------------------------------------------------------
# Timestamp generator — spread across the last 14 days, weighted toward recent
# ---------------------------------------------------------------------------
NOW = datetime.now(tz=timezone.utc)

def _timestamp() -> datetime:
    """Random timestamp in the last 14 days, slightly weighted toward recent days."""
    # Exponential-like weighting: more recent = more likely
    days_ago = random.betavariate(1.2, 2.8) * 14  # peaks near 0-3 days ago
    hours_offset = random.uniform(6, 22)  # business hours only
    ts = NOW - timedelta(days=days_ago, hours=0)
    ts = ts.replace(hour=int(hours_offset), minute=random.randint(0, 59), second=random.randint(0, 59))
    return ts


# ---------------------------------------------------------------------------
# External payment ID generator (Razorpay-style)
# ---------------------------------------------------------------------------

def _payment_id() -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    suffix = "".join(random.choices(chars, k=14))
    return f"pay_{suffix}"


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def build_records() -> list[dict]:
    """Build all 120 transaction dicts."""
    records = []

    # Decide which ~8% will have dnd_opt_out=True
    dnd_indices = set(random.sample(range(TOTAL), k=round(TOTAL * DND_RATE)))

    from typing import cast
    idx = 0
    for cat in CATEGORIES:
        cat_count = cast(int, cat["count"])
        amount_prof = cast(str, cat["amount_profile"])
        reasons_list = cast(list[str], cat["reasons"])
        cat_enum = cast(RootCauseCategory, cat["category"])
        for _ in range(cat_count):
            bank = random.choices(BANKS, weights=BANK_WEIGHTS, k=1)[0]
            records.append(
                {
                    "external_payment_id": _payment_id(),
                    "customer_id": f"cust_{fake.uuid4()[:8]}",
                    "customer_name": fake.name(),
                    "amount": _amount(amount_prof),
                    "currency": "INR",
                    "failure_reason": random.choice(reasons_list),
                    "gateway": random.choice(GATEWAYS),
                    "bank": bank,
                    "status": TransactionStatus.failed,
                    "dnd_opt_out": idx in dnd_indices,
                    "retry_count": 0,
                    "last_action_at": None,
                    "created_at": _timestamp(),
                    # Stash category for verification (not a DB column)
                    "_category": cat_enum.value,
                }
            )
            idx += 1

    # Shuffle so batch isn't in category order
    random.shuffle(records)
    return records


def _print_summary(session) -> None:
    """Query DB and print a distribution summary table."""
    from sqlalchemy import func
    from app.models.models import Classification

    # We don't have classifications yet — summarise by failure_reason keyword heuristic
    total = session.query(Transaction).count()
    dnd = session.query(Transaction).filter(Transaction.dnd_opt_out == True).count()

    # Amount stats
    amounts = [r[0] for r in session.query(Transaction.amount).all()]
    avg_amt = sum(amounts) / len(amounts)
    min_amt = min(amounts)
    max_amt = max(amounts)

    # Status counts
    print("\n" + "=" * 60)
    print("  Recovr — Synthetic Batch Summary")
    print("=" * 60)
    print(f"  Total records   : {total}")
    print(f"  DND opt-out     : {dnd} ({dnd/total*100:.1f}%)")
    print(f"  Amount range    : INR {min_amt:,.0f} – {max_amt:,.0f}")
    print(f"  Average amount  : INR {avg_amt:,.0f}")

    # Keyword-based category identification (precise, non-overlapping)
    categories = {
        "card_declined":        ("card declin", "do not honour", "reported stolen", "recurring"),
        "insufficient_funds":   ("insufficient fund", "insufficient balance", "debit failed - insufficient"),
        "gateway_timeout":      ("gateway timeout", "gateway request", "timed out", "unreachable", "network timeout", "connection to payment"),
        "bank_downtime":        ("issuing bank", "core banking", "maintenance", "sla", "bank undergoing", "bank not responding", "bank server"),
        "otp_failure":          ("otp", "3d secure", "authentication"),
        "fraud_false_positive": ("fraud", "risk engine", "velocity", "suspicious"),
    }
    TARGET = {
        "card_declined": 36,
        "insufficient_funds": 24,
        "gateway_timeout": 24,
        "bank_downtime": 18,
        "otp_failure": 12,
        "fraud_false_positive": 6,
    }

    rows = session.query(Transaction.failure_reason).all()
    reasons = [r[0].lower() for r in rows]

    print("\n  Category Distribution")
    print(f"  {'Category':<26} {'Count':>5}  {'Actual%':>7}  {'Target%':>7}  {'Target#':>7}")
    print("  " + "-" * 56)
    for cat, keywords in categories.items():
        count = sum(1 for r in reasons if any(k in r for k in keywords))
        target_n = TARGET[cat]
        print(
            f"  {cat:<26} {count:>5}  {count/total*100:>6.1f}%  "
            f"{target_n/total*100:>6.1f}%  {target_n:>6}"
        )

    # Bank distribution
    print("\n  Bank Distribution")
    bank_counts: dict[str, int] = {}
    for r in session.query(Transaction.bank).all():
        bank_counts[r[0]] = bank_counts.get(r[0], 0) + 1
    for bank, cnt in sorted(bank_counts.items(), key=lambda x: -x[1]):
        print(f"    {bank:<32} {cnt:>3} ({cnt/total*100:.1f}%)")

    print("=" * 60)


def run() -> None:
    session = SessionLocal()
    try:
        # -- Idempotent: clear all existing data (CASCADE handles child tables)
        print("[INFO] Clearing existing transaction data (CASCADE)...")
        session.execute(text("TRUNCATE TABLE transactions RESTART IDENTITY CASCADE"))
        session.commit()
        print("[OK]   Cleared.")

        # -- Build and insert records
        print(f"[INFO] Generating {TOTAL} synthetic records...")
        records = build_records()

        tx_objects = []
        for rec in records:
            rec_clean = {k: v for k, v in rec.items() if not k.startswith("_")}
            tx_objects.append(Transaction(**rec_clean))

        session.add_all(tx_objects)
        session.commit()
        print(f"[OK]   Inserted {len(tx_objects)} records.")

        # -- Print distribution summary
        _print_summary(session)

    except Exception as exc:
        session.rollback()
        print(f"[FAIL] Generation failed: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()
