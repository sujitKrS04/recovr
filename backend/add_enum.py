from app.core.database import SessionLocal
from sqlalchemy import text
s = SessionLocal()
s.execute(text("ALTER TYPE transaction_status ADD VALUE IF NOT EXISTS 'suppressed'"))
s.commit()
print('Added suppressed to enum')
