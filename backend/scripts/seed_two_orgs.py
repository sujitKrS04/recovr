"""
Seed two separate organizations with one admin user each and 120 sample transactions per org.

Demonstrates per-org data isolation & batch execution:
  - Org A (slug=acme)   → admin: alice@acme.com / password123 (120 transactions)
  - Org B (slug=globex) → admin: bob@globex.com / password456 (120 transactions)

Run from backend/:
    python scripts/seed_two_orgs.py
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.auth_models import Organization, User, UserRole
from app.models.models import Transaction, TransactionStatus
from scripts.generate_batch import build_records, SEED

ORGS = [
    {
        "slug": "acme",
        "name": "Acme Corp",
        "admin_email": "alice@acme.com",
        "admin_password": "password123",
        "admin_name": "Alice Admin",
        "seed_offset": 0,
    },
    {
        "slug": "globex",
        "name": "Globex Inc",
        "admin_email": "bob@globex.com",
        "admin_password": "password456",
        "admin_name": "Bob Admin",
        "seed_offset": 1000,
    },
]


def seed():
    db = SessionLocal()
    try:
        for spec in ORGS:
            # 1. Get or create Organization
            org = db.query(Organization).filter(Organization.slug == spec["slug"]).first()
            if not org:
                org = Organization(slug=spec["slug"], name=spec["name"])
                db.add(org)
                db.flush()
                print(f"[created] Org '{spec['slug']}' (id={org.id})")
            else:
                print(f"[found] Org '{spec['slug']}' (id={org.id})")

            # 2. Get or create Admin User
            user = db.query(User).filter(User.email == spec["admin_email"]).first()
            if not user:
                user = User(
                    org_id=org.id,
                    email=spec["admin_email"],
                    hashed_password=hash_password(spec["admin_password"]),
                    full_name=spec["admin_name"],
                    role=UserRole.admin,
                )
                db.add(user)
                db.flush()
                print(f"[created] User '{spec['admin_email']}' (id={user.id})")
            else:
                print(f"[found] User '{spec['admin_email']}' (id={user.id})")

            # 3. Ensure Org has 120 starter transactions
            existing_tx_count = db.query(Transaction).filter(Transaction.org_id == org.id).count()
            if existing_tx_count == 0:
                # Generate batch of 120 transactions for this org
                random.seed(SEED + spec["seed_offset"])
                raw_records = build_records()
                tx_objects = []
                for idx, rec in enumerate(raw_records):
                    rec_clean = {k: v for k, v in rec.items() if not k.startswith("_")}
                    # Ensure unique external_payment_id per org
                    rec_clean["external_payment_id"] = f"pay_{spec['slug']}_{idx+1:04d}"
                    rec_clean["org_id"] = org.id
                    tx_objects.append(Transaction(**rec_clean))

                db.add_all(tx_objects)
                db.flush()
                print(f"[created] {len(tx_objects)} transactions for Org '{spec['slug']}' (org_id={org.id})")
            else:
                print(f"[found] {existing_tx_count} existing transaction(s) for Org '{spec['slug']}'")

        db.commit()
        print("\nSeed complete.")
        print("\nCredentials:")
        for spec in ORGS:
            print(f"  {spec['admin_email']} / {spec['admin_password']}  ->  {spec['slug']}")
    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
