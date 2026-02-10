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
    {
        "name": "Address detection (building + Anna Salai + masked PIN)",
        "input": "Kasturi Buildings\n859 & 860 Anna Salai\nChennai - 6xxxxx",
        "must_contain": "[REDACTED_ADDRESS",
        "must_not_contain": "Anna Salai",
    },
    {
        "name": "Address detection (road with building prefix and numeric suffix)",
        "input": "Registered Office: Kasturi Buildings, 859 & 860 Anna Salai, Chennai - 600002",
        "must_contain": "[REDACTED_ADDRESS",
        "must_not_contain": "Kasturi Buildings",
    },
    {
        "name": "Address detection (Nagar legal notice style)",
        "input": "Address: No. 12, Lakshmi Nagar Extension, Chennai - 600034",
        "must_contain": "[REDACTED_ADDRESS",
        "must_not_contain": "Lakshmi Nagar",
    },
    {
        "name": "Address detection (road-only line followed by more tokens)",
        "input": "Address: Anna Salai Chennai 600002",
        "must_contain": "[REDACTED_ADDRESS",
        "must_not_contain": "Anna Salai",
    },
    {
        "name": "Entity detection (backward compatible Pvt. Ltd. suffix)",
        "input": "The agreement is with Acme Pvt. Ltd. for services.",
        "must_contain": "[REDACTED_PRIVATE_LIMITED",
        "must_not_contain": "Acme Pvt. Ltd.",
    },
    {
        "name": "Entity detection (multi-token legal suffix with apostrophe)",
        "input": "Notice was issued by Harbor View Owner's Association, Mumbai.",
        "must_contain": "[REDACTED_ENTITY",
        "must_not_contain": "Harbor View Owner's Association",
    },
    {
        "name": "Entity detection (multi-token legal suffix with punctuation)",
        "input": "Representative of Apex Audit Firm: Mr. Rajesh Sharma attended.",
        "must_contain": "[REDACTED_ENTITY",
        "must_not_contain": "Apex Audit Firm",
    },
]

passed = 0
failed = 0
for tc in test_cases:
    tracker = PIITracker()
    result = redact_text(tc["input"], tracker)
    ok = True
    must_contain = tc.get("must_contain")
    must_contain_any = tc.get("must_contain_any")
    if must_contain and must_contain not in result:
        print(f"FAIL: {tc['name']} — expected '{must_contain}' in result")
        print(f"  Got: {result}")
        ok = False
    if must_contain_any and not any(token in result for token in must_contain_any):
        print(f"FAIL: {tc['name']} — expected one of {must_contain_any} in result")
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
