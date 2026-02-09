"""
Comprehensive Indian PII detection patterns and dictionaries.
"""
import re

from generated_indian_names import INDIAN_FIRST_NAMES, INDIAN_SURNAMES

# ============================================================
# REGEX PATTERNS  (ordered: most‑specific → least‑specific)
# ============================================================
MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

PII_REGEX_PATTERNS = [
    # GST Number  – 15 chars, embeds PAN; must come first
    ("GST_NUMBER", re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]\b")),

    # Aadhaar Number – 12 digits with optional separators
    ("AADHAAR_NUMBER", re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b")),

    # IFSC Code – 4 letters + '0' + 6 alphanumeric
    ("IFSC_CODE", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),

    # PAN Number – ABCDE1234F
    ("PAN_NUMBER", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),

    # Voter ID (EPIC) – 3 letters + 7 digits
    ("VOTER_ID", re.compile(r"\b[A-Z]{3}\d{7}\b")),

    # Indian Passport – letter + 7 digits
    ("PASSPORT_NUMBER", re.compile(r"\b[A-HJ-NP-Z]\d{7}\b")),

    # Driving License – state code + RTO + year + serial
    ("DRIVING_LICENSE", re.compile(
        r"\b[A-Z]{2}[\s\-/]?\d{2,3}[\s\-/]?\d{4}[\s\-/]?\d{5,7}\b"
    )),

    # Vehicle Registration – KA 01 AB 1234
    ("VEHICLE_REGISTRATION", re.compile(
        r"\b[A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{4}\b"
    )),

    # UPI ID – before email to avoid overlap
    ("UPI_ID", re.compile(
        r"\b[a-zA-Z0-9._\-]+@(?:upi|paytm|oksbi|okaxis|okicici|okhdfcbank|ybl|apl|ibl|axl|sbi|icici|hdfc|kotak|airtel|freecharge|jio|postbank|yesbank)\b",
        re.IGNORECASE,
    )),

    # Date of Birth – with context
    ("DATE_OF_BIRTH", re.compile(
        r"(?:D\.?O\.?B\.?|[Dd]ate\s+of\s+[Bb]irth|[Bb]orn\s+(?:on|in)|[Bb]irth\s*[Dd]ate)"
        r"[\s:.\-]*\d{1,2}(?:st|nd|rd|th)?(?:"
        r"[/.\-]\d{1,2}[/.\-]\d{2,4}"
        r"|[\s\-]+"
        + MONTH_PATTERN +
        r"(?:,?[\s\-]+)\d{2,4})",
    )),

    # Email Address
    ("EMAIL", re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    )),

    # Indian Phone Number  (+91 / 0‑prefix optional, starts 6‑9)
    # Handles spaces within the number: +91 62908 45190
    ("PHONE_NUMBER", re.compile(
        r"(?:\+91[\s\-]?)?(?:\(?0?\d{2,4}\)?[\s\-]?)?\b[6-9]\d{4}[\s\-]?\d{5}\b"
    )),

    # Bank Account (context‑dependent)
    ("BANK_ACCOUNT", re.compile(
        r"(?:(?:A/C|a/c|[Aa]ccount|ACC|Acc)[\s]*(?:No\.?|Number|#|:)?[\s]*)\d{9,18}\b"
    )),

    # Indian PIN Code – 6 digits, first digit 1‑9, optional middle space
    ("PIN_CODE", re.compile(r"\b[1-9]\d{2}\s?\d{3}\b")),
]


# ============================================================
# INDIAN CITIES  (Title Case – top ~90 cities)
# ============================================================
INDIAN_CITIES: set[str] = {
    "Agra", "Ahmedabad", "Ajmer", "Aligarh", "Allahabad", "Ambala",
    "Amritsar", "Aurangabad", "Bangalore", "Bengaluru", "Bareilly",
    "Bhopal", "Bhubaneswar", "Bikaner", "Chandigarh", "Chennai",
    "Coimbatore", "Cuttack", "Dehradun", "Delhi", "Dhanbad", "Durgapur",
    "Ernakulam", "Faridabad", "Ghaziabad", "Gorakhpur", "Guntur",
    "Gurgaon", "Gurugram", "Guwahati", "Gwalior", "Howrah", "Hubli",
    "Hyderabad", "Indore", "Jabalpur", "Jaipur", "Jalandhar",
    "Jamnagar", "Jamshedpur", "Jodhpur", "Kanpur", "Kochi", "Kolhapur",
    "Kolkata", "Kota", "Kozhikode", "Lucknow", "Ludhiana", "Madurai",
    "Mangalore", "Meerut", "Moradabad", "Mumbai", "Mysore", "Mysuru",
    "Nagpur", "Nanded", "Nashik", "Navi Mumbai", "Noida", "Patna",
    "Pimpri-Chinchwad", "Pondicherry", "Pune", "Raipur", "Rajahmundry",
    "Rajkot", "Ranchi", "Salem", "Secunderabad", "Shimla", "Siliguri",
    "Solapur", "Srinagar", "Surat", "Thane", "Thiruvananthapuram",
    "Tiruchirappalli", "Tiruppur", "Trichy", "Udaipur", "Ujjain",
    "Vadodara", "Varanasi", "Vijayawada", "Visakhapatnam", "Warangal",
}

# ============================================================
# INDIAN STATES & UNION TERRITORIES  (full names)
# ============================================================
INDIAN_STATES: set[str] = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
}
