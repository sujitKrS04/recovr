"""Verify actual inserted row counts by querying the DB directly."""
from app.core.database import SessionLocal
from app.models.models import Transaction, TransactionStatus
from sqlalchemy import func

CATEGORY_KEYWORDS = {
    "card_declined":        ["card declin", "do not honour", "reported stolen", "recurring"],
    "insufficient_funds":   ["insufficient fund", "insufficient balance", "debit failed - insufficient"],
    "gateway_timeout":      ["gateway timeout", "gateway request", "timed out", "unreachable", "network timeout", "connection to payment"],
    "bank_downtime":        ["issuing bank", "core banking", "maintenance", "sla", "bank undergoing", "bank not responding", "bank server"],
    "otp_failure":          ["otp", "3d secure", "authentication"],
    "fraud_false_positive": ["fraud", "risk engine", "velocity", "suspicious"],
}

TARGET = {
    "card_declined": 36,
    "insufficient_funds": 24,
    "gateway_timeout": 24,
    "bank_downtime": 18,
    "otp_failure": 12,
    "fraud_false_positive": 6,
}

session = SessionLocal()
total = session.query(Transaction).count()
rows = [(r[0].lower(),) for r in session.query(Transaction.failure_reason).all()]

print(f"\nTotal rows: {total}")
print(f"\n{'Category':<26} {'Matched':>7} {'Target':>7} {'OK?':>5}")
print("-" * 50)

grand = 0
for cat, keywords in CATEGORY_KEYWORDS.items():
    count = sum(1 for (r,) in rows if any(k in r for k in keywords))
    grand += count
    ok = "[OK]" if count == TARGET[cat] else "[!!]"
    print(f"{cat:<26} {count:>7} {TARGET[cat]:>7} {ok:>5}")

print(f"\nTotal matched by keywords: {grand} / {total}")

# Also check amounts
amounts = [float(r[0]) for r in session.query(Transaction.amount).all()]
dnd_count = session.query(Transaction).filter(Transaction.dnd_opt_out == True).count()

print(f"\nAmount stats:")
print(f"  Min: INR {min(amounts):,.0f}")
print(f"  Max: INR {max(amounts):,.0f}")
print(f"  Avg: INR {sum(amounts)/len(amounts):,.0f}")
print(f"\nDND opt-out: {dnd_count} ({dnd_count/total*100:.1f}%)")

session.close()
