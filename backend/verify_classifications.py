"""Verify classifications table after run_classifier."""
from app.core.database import SessionLocal
from app.models.models import Classification, ClassifierMethod

session = SessionLocal()
total = session.query(Classification).count()
rule_n = session.query(Classification).filter(Classification.classifier_method == ClassifierMethod.rule).count()
llm_n  = session.query(Classification).filter(Classification.classifier_method == ClassifierMethod.llm).count()

from sqlalchemy import func
avg_conf = session.query(func.avg(Classification.confidence)).scalar()

print(f"[OK] Classifications in DB: {total}")
print(f"     Rule-based : {rule_n} ({rule_n/total*100:.1f}%)")
print(f"     LLM        : {llm_n}  ({llm_n/total*100:.1f}%)")
print(f"     Avg conf   : {float(avg_conf):.3f}")
assert total == 120, f"Expected 120, got {total}"
assert rule_n == 114, f"Expected 114 rule, got {rule_n}"
assert llm_n == 6, f"Expected 6 LLM, got {llm_n}"
print("[OK] All assertions passed.")
session.close()
