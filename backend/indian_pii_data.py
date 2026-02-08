"""
Comprehensive Indian PII detection patterns and dictionaries.
"""
import re

# ============================================================
# REGEX PATTERNS  (ordered: most‑specific → least‑specific)
# ============================================================
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
        r"[\s:.\-]*\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}",
    )),

    # Email Address
    ("EMAIL", re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    )),

    # Indian Phone Number  (+91 / 0‑prefix optional, starts 6‑9)
    ("PHONE_NUMBER", re.compile(
        r"(?:\+91[\s\-]?)?(?:\(?0?\d{2,4}\)?[\s\-]?)?\b[6-9]\d{9}\b"
    )),

    # Bank Account (context‑dependent)
    ("BANK_ACCOUNT", re.compile(
        r"(?:(?:A/C|a/c|[Aa]ccount|ACC|Acc)[\s]*(?:No\.?|Number|#|:)?[\s]*)\d{9,18}\b"
    )),

    # Address fragments – flat/house/plot + number
    ("ADDRESS", re.compile(
        r"(?:(?:[Ff]lat|[Hh]ouse|[Pp]lot|[Rr]oom|[Dd]oor|[Bb]uilding|[Bb]lock|[Ss]ector|[Pp]hase|[Ww]ard)"
        r"\s*(?:[Nn]o\.?|[Nn]umber|#)?[\s:.\-]*[\w\-/]+)",
    )),

    # Indian PIN Code – 6 digits, first digit 1‑9
    ("PIN_CODE", re.compile(r"\b[1-9]\d{5}\b")),
]


# ============================================================
# INDIAN FIRST NAMES  (Title Case, >= 3 chars to avoid noise)
# ============================================================
INDIAN_FIRST_NAMES: set[str] = {
    # Male
    "Aarav", "Aadhya", "Aakash", "Aayush", "Abhinav", "Abhishek", "Aditya",
    "Ajay", "Ajit", "Akash", "Akhil", "Akshay", "Amaan", "Amar", "Ameet",
    "Amit", "Amitabh", "Amrish", "Anand", "Aniket", "Anil", "Anirban",
    "Anish", "Ankit", "Ankur", "Anoop", "Anshul", "Anurag", "Apoorv",
    "Arjun", "Arnab", "Arun", "Aryan", "Ashish", "Ashok", "Ashwin",
    "Atharv", "Atul", "Avinash", "Balaji", "Bhaskar", "Bhavesh", "Bikram",
    "Chandan", "Chirag", "Darshan", "Deepak", "Devendra", "Dheeraj",
    "Dhruv", "Dilip", "Dinesh", "Dipak", "Ganesh", "Gaurav", "Girish",
    "Gopal", "Govind", "Gururaj", "Hardik", "Harish", "Hemant", "Hitesh",
    "Indrajit", "Ishaan", "Jagdish", "Jatin", "Jayant", "Jayesh",
    "Kailash", "Kamal", "Karan", "Karthik", "Kartik", "Kaushik", "Kishore",
    "Krishna", "Kunal", "Lalit", "Lokesh", "Madhav", "Mahendra", "Mahesh",
    "Manish", "Manoj", "Mayank", "Milind", "Mohit", "Mukesh", "Mukund",
    "Murali", "Nagendra", "Nandan", "Narayan", "Narendra", "Naveen",
    "Neeraj", "Nikhil", "Nilesh", "Nitin", "Omkar", "Pankaj", "Paresh",
    "Pavan", "Pawan", "Pradeep", "Prakash", "Pranav", "Prashant", "Pratik",
    "Praveen", "Prem", "Puneet", "Raghav", "Rahul", "Rajat", "Rajendra",
    "Rajesh", "Rajiv", "Rakesh", "Raman", "Ramesh", "Ranveer", "Ravi",
    "Rishabh", "Ritesh", "Rohit", "Roshan", "Sachin", "Sahil", "Samar",
    "Sandeep", "Sanjay", "Sanjiv", "Santosh", "Saran", "Satish", "Saurabh",
    "Shankar", "Shashank", "Shekhar", "Shiv", "Shivam", "Shoaib",
    "Shubham", "Siddharth", "Soham", "Sourabh", "Srikanth", "Subhash",
    "Sudhir", "Sumit", "Sunil", "Suraj", "Suresh", "Swapnil", "Tanmay",
    "Tarun", "Tushar", "Varun", "Venkat", "Venkatesh", "Vijay", "Vikas",
    "Vikram", "Vinay", "Vinod", "Vipin", "Vishal", "Vivek", "Yash",
    "Yogesh",
    # Female
    "Aarti", "Aditi", "Aishwarya", "Akanksha", "Amrita", "Ananya", "Aneeta",
    "Angira", "Anita", "Anjali", "Ankita", "Anupriya", "Anusha", "Aparna",
    "Archana", "Aruna", "Bhavna", "Bhawana", "Chandni", "Chitra", "Deepa",
    "Deepika", "Devi", "Devika", "Dimple", "Divya", "Durga", "Ekta",
    "Gayatri", "Geeta", "Geetanjali", "Harini", "Hema", "Indira", "Ishita",
    "Jaya", "Jayanthi", "Jyoti", "Jyotsna", "Kajal", "Kamini", "Kaveri",
    "Kavita", "Kiran", "Komal", "Kriti", "Lakshmi", "Lata", "Latika",
    "Madhuri", "Mamta", "Manisha", "Meena", "Meenakshi", "Meera",
    "Megha", "Mira", "Mohini", "Mona", "Namita", "Nandini", "Neelam",
    "Neena", "Neha", "Nidhi", "Nikita", "Nimisha", "Nisha", "Nita",
    "Padma", "Pallavi", "Payal", "Pooja", "Poonam", "Prabhavati",
    "Prachi", "Pragya", "Pratibha", "Preeti", "Prerna", "Priya",
    "Priyanka", "Puja", "Radha", "Rajni", "Rakhi", "Rashmi", "Ratna",
    "Rekha", "Renuka", "Richa", "Rina", "Ritu", "Riya", "Roshni",
    "Rupali", "Sadhana", "Sandhya", "Sangeeta", "Sapna", "Sarita",
    "Savita", "Seema", "Shabnam", "Shanti", "Shilpa", "Shipra", "Shivani",
    "Shobha", "Shreya", "Shruti", "Simran", "Sita", "Smita", "Sneha",
    "Sonal", "Sonali", "Sonia", "Suchitra", "Sudha", "Sujata", "Sulochana",
    "Sunita", "Surbhi", "Surekha", "Sushma", "Swati", "Sweta", "Tanvi",
    "Tara", "Usha", "Vandana", "Varsha", "Veena", "Vidya", "Yamini",
}

# ============================================================
# INDIAN SURNAMES  (Title Case)
# ============================================================
INDIAN_SURNAMES: set[str] = {
    "Acharya", "Agarwal", "Aggarwal", "Agrawal", "Ahuja", "Anand",
    "Arora", "Babu", "Bajaj", "Bajpai", "Bala", "Balakrishnan",
    "Banerjee", "Basu", "Bedi", "Bhandari", "Bhardwaj", "Bhat",
    "Bhatia", "Bhatnagar", "Bhatt", "Bhattacharya", "Biswas", "Bose",
    "Chakraborty", "Chandra", "Chatterjee", "Chattopadhyay", "Chauhan",
    "Chawla", "Choudhary", "Choudhury", "Chopra", "Daga", "Das",
    "Dasgupta", "Deshpande", "Deshmukh", "Dewan", "Dhawan", "Dixit",
    "Dubey", "Dutta", "Dwivedi", "Gaikwad", "Gandhi", "Ganguly",
    "Ghosh", "Gill", "Goel", "Goswami", "Goyal", "Grover", "Gulati",
    "Gupta", "Hegde", "Iyer", "Iyengar", "Jain", "Jadhav", "Jaiswal",
    "Jha", "Johar", "Joshi", "Kadam", "Kamath", "Kamboj", "Kapoor",
    "Kashyap", "Kaul", "Kaur", "Khanna", "Khatri", "Kohli", "Kulkarni",
    "Kumar", "Lal", "Mahajan", "Maheswari", "Malhotra", "Malik", "Mane",
    "Mathur", "Mehra", "Mehta", "Menon", "Mishra", "Misra", "Mitra",
    "Modi", "Mohan", "Mukherjee", "Murthy", "Nag", "Naidu", "Naik",
    "Nair", "Nambiar", "Nanda", "Narayan", "Nath", "Nayak", "Negi",
    "Oberoi", "Padmanabhan", "Pal", "Pande", "Pandey", "Pandit", "Pant",
    "Parikh", "Parmar", "Patel", "Pathak", "Patil", "Pawar", "Pillai",
    "Prasad", "Purohit", "Raghavan", "Rai", "Raina", "Raja", "Rajan",
    "Rajput", "Raju", "Ramachandran", "Raman", "Ramaswamy", "Rana",
    "Ranganathan", "Rao", "Rathore", "Rawat", "Reddy", "Roy",
    "Sachdev", "Saha", "Sahni", "Saini", "Saluja", "Saxena", "Sen",
    "Sengupta", "Seth", "Sethi", "Shah", "Shankar", "Sharma", "Shastri",
    "Shekhar", "Shinde", "Shrivastava", "Shukla", "Singh", "Sinha",
    "Sodhi", "Soni", "Sood", "Sreedharan", "Sridhar", "Srinivas",
    "Srinivasan", "Subramanian", "Suri", "Swamy", "Tandon", "Thakkar",
    "Thakur", "Tiwari", "Trehan", "Tripathi", "Trivedi", "Upadhyay",
    "Varma", "Vashisht", "Vats", "Venkataraman", "Verma", "Vohra",
    "Wadhwa", "Walia", "Yadav",
}

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
