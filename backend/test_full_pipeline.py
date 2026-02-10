"""End-to-end test for the full PII redaction pipeline."""

from pii_engine import PIITracker, redact_text


test_cases = [
    {
        "name": "Aadhaar detection (regex)",
        "input": "My Aadhaar number is 2345 6789 0123",
        "must_contain": "[REDACTED_AADHAAR_NUMBER",
        "must_not_contain": "2345",
    },
    {
        "name": "PAN detection (regex)",
        "input": "PAN: ABCDE1234F",
        "must_contain": "[REDACTED_PAN_NUMBER",
        "must_not_contain": "ABCDE1234F",
    },
    {
        "name": "Name detection (NLP)",
        "input": "Mr. Rajesh Sharma attended the meeting",
        "must_contain": "[REDACTED_INDIVIDUAL",
        "must_not_contain": None,
    },
    {
        "name": "Location detection (NLP)",
        "input": "The office is located in Bangalore, Karnataka",
        "must_contain": "[REDACTED_LOCATION",
        "must_not_contain": None,
    },
    {
        "name": "Email detection (regex)",
        "input": "Contact me at test.user@example.com",
        "must_contain": "[REDACTED_EMAIL",
        "must_not_contain": "test.user@example.com",
    },
    {
        "name": "Phone detection (regex)",
        "input": "Call me at +91 98765 43210",
        "must_contain": "[REDACTED_PHONE_NUMBER",
        "must_not_contain": "98765",
    },
]

passed = 0
failed = 0
for tc in test_cases:
    tracker = PIITracker()
    result = redact_text(tc["input"], tracker)
    ok = True
    if tc["must_contain"] and tc["must_contain"] not in result:
        print(f"FAIL: {tc['name']} — expected '{tc['must_contain']}' in result")
        print(f"  Got: {result}")
        ok = False
    if tc["must_not_contain"] and tc["must_not_contain"] in result:
        print(f"FAIL: {tc['name']} — did not expect '{tc['must_not_contain']}' in result")
        print(f"  Got: {result}")
        ok = False
    if ok:
        print(f"PASS: {tc['name']}")
        passed += 1
    else:
        failed += 1

print(f"\n{passed} passed, {failed} failed out of {len(test_cases)} tests.")
