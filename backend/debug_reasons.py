"""Debug: show the exact failure_reason strings that don't match any keyword."""
from app.core.database import SessionLocal
from app.models.models import Transaction

ALL_KEYWORDS = [
    "card declin", "do not honour", "reported stolen", "recurring",
    "insufficient fund", "insufficient balance", "debit failed - insufficient",
    "gateway timeout", "gateway request", "timed out", "unreachable",
    "network timeout", "connection to payment",
    "issuing bank", "core banking", "maintenance", "sla",
    "bank undergoing", "bank not responding", "bank server",
    "otp", "3d secure", "authentication",
    "fraud", "risk engine", "velocity", "suspicious",
]

session = SessionLocal()
rows = [(r[0],) for r in session.query(Transaction.failure_reason).all()]
unmatched = [(r,) for (r,) in rows if not any(k in r.lower() for k in ALL_KEYWORDS)]
print(f"Unmatched reasons ({len(unmatched)}):")
for (r,) in unmatched:
    print(f"  '{r}'")
session.close()
