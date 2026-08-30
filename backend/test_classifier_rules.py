"""
Quick smoke-test for the rule-based classifier.
Tests every expected failure reason string from the batch generator against expected category.
Run: .venv\\Scripts\\python test_classifier_rules.py
"""
from app.services.classifier import rule_classify
from app.models.models import RootCauseCategory

TEST_CASES = [
    # (failure_reason_string, expected_category, should_be_ruled)
    # card_declined
    ("Card declined - Insufficient credit limit", RootCauseCategory.card_declined, True),
    ("Card declined - Expired card", RootCauseCategory.card_declined, True),
    ("Card declined - Card blocked by issuer", RootCauseCategory.card_declined, True),
    ("Card declined - Do not honour", RootCauseCategory.card_declined, True),
    ("Card declined - Card reported stolen", RootCauseCategory.card_declined, True),
    ("Card declined - Card not set up for recurring payments", RootCauseCategory.card_declined, True),
    # insufficient_funds
    ("Insufficient funds in account", RootCauseCategory.insufficient_funds, True),
    ("Insufficient balance - debit failed", RootCauseCategory.insufficient_funds, True),
    ("Debit failed - insufficient balance", RootCauseCategory.insufficient_funds, True),
    # gateway_timeout
    ("Payment gateway request timed out", RootCauseCategory.gateway_timeout, True),
    ("Connection to payment processor lost", RootCauseCategory.gateway_timeout, True),
    ("Gateway timeout after 30s", RootCauseCategory.gateway_timeout, True),
    ("Upstream payment provider unreachable", RootCauseCategory.gateway_timeout, True),
    ("Network timeout during payment processing", RootCauseCategory.gateway_timeout, True),
    # bank_downtime
    ("Issuing bank server unavailable", RootCauseCategory.bank_downtime, True),
    ("Bank undergoing scheduled maintenance", RootCauseCategory.bank_downtime, True),
    ("Core banking system temporarily down", RootCauseCategory.bank_downtime, True),
    ("Bank not responding within SLA window", RootCauseCategory.bank_downtime, True),
    # otp_failure
    ("OTP verification failed - incorrect OTP entered", RootCauseCategory.otp_failure, True),
    ("OTP expired before submission", RootCauseCategory.otp_failure, True),
    ("3D Secure authentication failed", RootCauseCategory.otp_failure, True),
    ("OTP not received by customer", RootCauseCategory.otp_failure, True),
    # fraud_false_positive — MUST return None from rule_classify
    ("Transaction flagged by automated fraud detection", None, False),
    ("Risk engine declined - unusual spending pattern", None, False),
    ("Velocity check triggered - multiple attempts", None, False),
    ("Suspicious activity flag from issuer's risk system", None, False),
]

passed = 0
failed = 0

print(f"\n{'Failure Reason':<55} {'Expected':<22} {'Got':<22} {'OK?':>4}")
print("-" * 110)

for reason, expected_cat, should_rule in TEST_CASES:
    result = rule_classify(reason)

    if not should_rule:
        # Fraud cases should return None
        ok = result is None
        got_str = "None (-> LLM)" if result is None else f"WRONGLY MATCHED: {result.root_cause_category.value}"
        exp_str = "None (-> LLM)"
    else:
        ok = result is not None and result.root_cause_category == expected_cat
        got_str = result.root_cause_category.value if result else "None (-> LLM)"
        exp_str = expected_cat.value if expected_cat else "None"

    status = "[OK]" if ok else "[FAIL]"
    if ok:
        passed += 1
    else:
        failed += 1

    short_reason = reason[:54]
    print(f"{short_reason:<55} {exp_str:<22} {got_str:<22} {status:>4}")

print(f"\nResult: {passed} passed, {failed} failed out of {len(TEST_CASES)} test cases.")
if failed > 0:
    print("[FAIL] Some rule tests failed — review classifier.py patterns.")
    exit(1)
else:
    print("[OK] All rule-based classifier tests passed.")
