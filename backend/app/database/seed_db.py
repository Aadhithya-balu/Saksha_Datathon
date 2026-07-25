"""Seed roles, operators, and an ER-shaped prototype crime dataset."""
import random
from datetime import date, datetime, timedelta
from math import cos, sin
from random import uniform

from app.core.security import hash_password
from app.database.postgres import SessionLocal
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.notification import Notification
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim
from app.models.chain_of_custody import ChainOfCustody

ROLES = ["admin", "crime_analyst", "investigator", "policymaker"]

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@saksha.local",
        "full_name": "Platform Administrator",
        "password": "564738",
        "role_name": "admin",
        "district": "State HQ",
        "station": "KSP HQ",
    },
    {
        "username": "SCRB-7740",
        "email": "scrb-7740@saksha.local",
        "full_name": "DCP Rajesh Kumar",
        "password": "123456",
        "role_name": "crime_analyst",
        "district": "Bengaluru Urban",
        "station": "SCRB HQ",
    },
    {
        "username": "IO-3921",
        "email": "io-3921@saksha.local",
        "full_name": "Inspector Meera Sen",
        "password": "456789",
        "role_name": "investigator",
        "district": "Mysuru",
        "station": "Devaraja Police Station",
        "badge_number": "IO-3921",
        "rank": "Inspector",
    },
    {
        "username": "SP-0088",
        "email": "sp-0088@saksha.local",
        "full_name": "SP Anil Kumble",
        "password": "987654",
        "role_name": "policymaker",
        "district": "State HQ",
        "station": "KSP HQ",
        "badge_number": "SP-0088",
        "rank": "Superintendent of Police",
    },
]

CATEGORIES = [
    ("Cyber Crime & Online Fraud", "IPC 420 / IT Act 66D", "high"),
    ("Theft & Burglaries", "IPC 379/457", "medium"),
    ("Narcotics Smuggling Services", "NDPS 21/22", "high"),
    ("Smuggling & Excise Violations", "Excise Act", "medium"),
    ("Assault", "IPC 323/324", "medium"),
    ("Illegal Mining Violations", "MMDR Act", "high"),
    ("Domestic Violence", "DV Act", "medium"),
    ("Property Disputes", "IPC 447/506", "low"),
]

LOCATIONS = [
    ("Whitefield Cyber Cell Beat", "Bengaluru Urban", "Whitefield Police Station", 12.9698, 77.7500, "560066"),
    ("KR Puram Transit Corridor", "Bengaluru Urban", "KR Puram Police Station", 13.0056, 77.6880, "560036"),
    ("Devaraja Market Zone", "Mysuru", "Devaraja Police Station", 12.2958, 76.6394, "570001"),
    ("Harbor Gate A", "Mangaluru", "Pandeshwar Police Station", 12.9050, 74.8350, "575001"),
    ("Khade Bazar Checkpoint", "Belagavi", "Khade Bazar Station", 15.8497, 74.4977, "590001"),
    ("Ballari Mines Sector B", "Ballari", "Rural Police Station", 15.1394, 76.9214, "583101"),
    ("Chowk Survey Layout", "Kalaburagi", "Chowk Police Station", 17.3297, 76.8343, "585101"),
    ("Hassan City East", "Hassan", "City Police Station", 13.0641, 76.1030, "573201"),
    ("Tumkuru Industrial Road", "Tumkuru", "Town Police Station", 13.3379, 77.1173, "572101"),
    ("Dharwad Market Yard", "Dharwad", "Suburban Police Station", 15.4589, 75.0078, "580001"),
]

CRIMINALS = [
    ("Ramu Swamy", "Kodaikanal Ramu", date(1982, 4, 12), "Male", "Scar near left eyebrow", "Night residential lock-break burglaries using scooter reconnaissance", "at_large"),
    ("Vikram Yadav", "Vicky", date(1990, 11, 7), "Male", "Spectacles, gold ring", "Money mule coordinator for app-based cyber extortion", "at_large"),
    ("Sayed Ibrahim", "Sayed", date(1985, 2, 22), "Male", "Tattoo on right wrist", "Port logistics support for synthetic drug consignments", "at_large"),
    ("Karthik Gowda", "Gowda", date(1988, 8, 3), "Male", "Thick moustache", "Forgery and property document intimidation", "arrested"),
    ("Mohsin Pasha", "Pasha", date(1987, 1, 19), "Male", "Burn mark on forearm", "Illegal mineral transport and forged transit slips", "at_large"),
    # 55 additional synthetic criminals for meaningful ML training
    ("Prasad Shenoy", "Prasad", date(1979, 6, 15), "Male", "Deep voice, tall build", "Cyber fraud via fake banking portals", "at_large"),
    ("Naveen Reddy", "Navi", date(1992, 3, 20), "Male", "Slim build, clean shaven", "Phishing SMS campaigns targeting elderly", "at_large"),
    ("Ravi Shankar Bhat", "Ravi Bhat", date(1981, 9, 8), "Male", "Gold chain, receding hairline", "Cash-in-transit robbery planning", "arrested"),
    ("Imran Khan Pathan", "Imran", date(1986, 12, 1), "Male", "Beard, muscular build", "Interstate drug mule coordinator", "at_large"),
    ("Deepak Sharma", "Deepu", date(1993, 7, 25), "Male", "Glasses, left ear piercing", "Online investment scam operator", "convicted"),
    ("Suresh Babu", "Suresh Anna", date(1975, 1, 30), "Male", "Greying temples", "Land grab intimidation syndicate", "at_large"),
    ("Manjunath Holla", "Manju", date(1983, 5, 14), "Male", "Stocky, red birthmark neck", "Stolen vehicle resale network", "at_large"),
    ("Farhan Ahmed", "Farhan", date(1991, 8, 22), "Male", "Sharp features, short hair", "Cryptocurrency money laundering", "at_large"),
    ("Girish Nayak", "Girish K", date(1984, 11, 3), "Male", "Wears thick spectacles", "Fake passport and visa racket", "arrested"),
    ("Venkatesh Kulkarni", "Venky", date(1980, 2, 18), "Male", "Mustache, broad forehead", "Contract killing intermediary", "at_large"),
    ("Yusuf Ali Khan", "Yusuf", date(1989, 4, 7), "Male", "Tattoo forearm, athletic build", "Smuggled electronics distribution", "at_large"),
    ("Rajesh Pai", "Raju Pai", date(1977, 10, 21), "Male", "Widow's peak, stocky", "Money lending extortion operations", "at_large"),
    ("Ashok Kamble", "Ashok", date(1994, 1, 12), "Male", "Earring, tattoo on neck", "ATM card skimming operations", "convicted"),
    ("Irfan Hassan", "Irfan", date(1988, 6, 29), "Male", "Lean, scar on chin", "Harbor smuggling logistics", "at_large"),
    ("Mahesh Jain", "Mahesh", date(1976, 3, 5), "Male", "Portly, thick glasses", "Property fraud and forged deeds", "arrested"),
    ("Vijay Kumar S", "Vijay S", date(1990, 9, 16), "Male", "Clean shaven, athletic", "Bike theft ring operator", "at_large"),
    ("Tanveer Alam", "Tanu", date(1987, 7, 2), "Male", "Tall, scar on forehead", "Fake currency distribution", "at_large"),
    ("Satish Mudiraj", "Satish", date(1983, 12, 8), "Male", "Dark complexion, muscular", "Illegal quarry operations", "at_large"),
    ("Rahul Deshpande", "Rahul D", date(1995, 2, 14), "Male", "Slim, ponytail", "Dark web drug marketplace admin", "at_large"),
    ("Bharath Gowda", "Bharath", date(1982, 8, 26), "Male", "Round face, gold teeth", "Timber smuggling coordinator", "arrested"),
    ("Javed Sheikh", "Javed", date(1991, 5, 19), "Male", "Tattoo chest, lean build", "Illegal mining transport driver", "at_large"),
    ("Santosh Patil", "Santosh P", date(1985, 11, 11), "Male", "Short, thick mustache", "IPC fraud and cheating", "at_large"),
    ("Arun Verma", "Arun V", date(1978, 4, 30), "Male", "Grey hair, spectacles", "Organized gambling den operator", "convicted"),
    ("Khalid Mehmood", "Khalid", date(1986, 3, 12), "Male", "Beard, heavy build", "Narcotics retail distribution", "at_large"),
    ("Pavan Kalyan R", "Pavan", date(1993, 10, 5), "Male", "Slim, clean shaven", "Cyber stalking and harassment", "at_large"),
    ("Shiva Prasad M", "Shiva M", date(1980, 7, 18), "Male", "Muscular, tribal tattoo", "Counterfeit goods manufacturing", "arrested"),
    ("Mohammed Ali", "Mohd Ali", date(1989, 1, 27), "Male", "Sharp nose, thin build", "Gold chain snatching gang leader", "at_large"),
    ("Ganesh Haldipur", "Ganesh", date(1984, 5, 9), "Male", "Round face, dimple", "Illegal transport route management", "at_large"),
    ("Rohit Shetty K", "Rohit K", date(1992, 11, 15), "Male", "Tall, sporty build", "Vehicle theft for parts", "arrested"),
    ("Zubair Sheikh", "Zubair", date(1981, 9, 3), "Male", "Beard, glasses", "Interstate sand mining syndicate", "at_large"),
    ("Nagendra Prasad", "Nagendra", date(1977, 6, 22), "Male", "Bald, strong jaw", "Extortion via threat calls", "at_large"),
    ("Vasanth Kumar", "Vasu", date(1994, 4, 11), "Male", "Slim, earring", "ATM break-in specialist", "convicted"),
    ("Hafeez Rehman", "Hafeez", date(1983, 12, 30), "Male", "Tall, broad build", "Smuggled gold transport", "at_large"),
    ("Chandrashekar B", "Chandru B", date(1988, 2, 8), "Male", "Mustache, medium build", "Fake document printing ring", "at_large"),
    ("Lokesh Biradar", "Lokesh", date(1990, 8, 17), "Male", "Scar on lip, stocky", "Illegal liquor distribution", "at_large"),
    ("Sameer Patel", "Sameer", date(1986, 10, 25), "Male", "Glasses, short hair", "Hawala money transfer operator", "arrested"),
    ("Rakesh Tiwari", "Rakesh T", date(1979, 3, 14), "Male", "Receding hairline, portly", "Land encroachment intimidation", "at_large"),
    ("Yogesh Shetty", "Yogesh", date(1991, 7, 6), "Male", "Athletic, tattoo arm", "Smuggled electronics import", "at_large"),
    ("Anil Kumar J", "Anil J", date(1985, 5, 23), "Male", "Thick mustache, medium build", "IPC assault repeat offender", "at_large"),
    ("Zaheer Ahmed", "Zaheer", date(1982, 11, 19), "Male", "Beard, lean build", "Drug courier network coordinator", "at_large"),
    ("Manoj Birajdar", "Manoj B", date(1993, 1, 7), "Male", "Short, muscular", "Illegal gambling enforcement", "convicted"),
    ("Sunil Khot", "Sunil K", date(1987, 9, 28), "Male", "Glasses, medium height", "Fake call center scam", "at_large"),
    ("Kiran Bhat", "Kiran", date(1980, 4, 16), "Male", "Portly, gold ring", "Timber transport forgery", "arrested"),
    ("Tariq Hussain", "Tariq", date(1992, 6, 2), "Male", "Lean, sharp features", "Illegal mineral transport", "at_large"),
    ("Vinayak Kulkarni", "Vinayak K", date(1984, 1, 25), "Male", "Tall, spectacles", "Cheque forgery operations", "at_large"),
    ("Nasir Shaikh", "Nasir", date(1989, 8, 14), "Male", "Short, heavy build", "Fish export smuggling", "at_large"),
]

VICTIMS = [
    ("K. S. Narayanan", "+91 98800 00001", "Bengaluru Urban", "Male", 52, "Reported biometric face ID bypass and loan extortion."),
    ("Dr. Vinay Murthy", "+91 98800 00002", "Mysuru", "Male", 46, "Reported night burglary and missing jewellery."),
    ("Asha Rao", "+91 98800 00003", "Mangaluru", "Female", 33, "Witnessed cargo handoff near harbor gate."),
    ("Prakash Jain", "+91 98800 00004", "Belagavi", "Male", 41, "Reported forged excise transport documents."),
    ("Latha Hegde", "+91 98800 00005", "Hassan", "Female", 29, "Filed domestic violence complaint with medical evidence."),
    ("Sunita Devi", "+91 98800 00006", "Bengaluru Urban", "Female", 38, "Lost savings in online investment scam."),
    ("Mohan Krishna", "+91 98800 00007", "Mysuru", "Male", 55, "Vehicle stolen from parking lot near market."),
    ("Fathima Begum", "+91 98800 00008", "Mangaluru", "Female", 42, "Gold chain snatched at traffic signal."),
    ("Rajendra Prasad", "+91 98800 00009", "Ballari", "Male", 48, "Land documents forged by fraudsters."),
    ("Shobha Patil", "+91 98800 00010", "Belagavi", "Female", 35, "Received threatening calls for loan recovery."),
    ("Nagaraj Shetty", "+91 98800 00011", "Tumkuru", "Male", 60, "Property encroachment with threat of violence."),
    ("Meena Kumari", "+91 98800 00012", "Kalaburagi", "Female", 44, "Husband involved in domestic abuse."),
    ("Pradeep Naik", "+91 98800 00013", "Dharwad", "Male", 37, "Shop broken into, cash and electronics stolen."),
    ("Suma B", "+91 98800 00014", "Hassan", "Female", 28, "Stalked and harassed online via social media."),
    ("Girijeshwar Rao", "+91 98800 00015", "Ballari", "Male", 50, "Illegal mining on ancestral land reported."),
    ("Ayesha Parveen", "+91 98800 00016", "Mangaluru", "Female", 31, "Hawala transfer scam victim."),
    ("Bharat Hegde", "+91 98800 00017", "Belagavi", "Male", 43, "ATM card cloned, account drained."),
    ("Chitra K", "+91 98800 00018", "Mysuru", "Female", 39, "Fake police impersonator demanded bribe."),
    ("Dinesh Rao", "+91 98800 00019", "Bengaluru Urban", "Male", 34, "Phishing email led to bank account compromise."),
    ("Eshwarappa", "+91 98800 00020", "Tumkuru", "Male", 58, "Farmland encroached by mining operators."),
    ("Farzana Banu", "+91 98800 00021", "Kalaburagi", "Female", 27, "Domestic violence with threats to children."),
    ("Gopal Krishna", "+91 98800 00022", "Dharwad", "Male", 45, "Property dispute turned violent."),
    ("Hema Malini", "+91 98800 00023", "Hassan", "Female", 52, "Jewellery stolen during house burglary."),
    ("Irfan Ahmed", "+91 98800 00024", "Mangaluru", "Male", 30, "Assaulted during road rage incident."),
    ("Jyothi Lingegowda", "+91 98800 00025", "Mysuru", "Female", 36, "Cyber fraud victim, lost retirement savings."),
]

# Original 11 cases + 49 synthetic cases = 60 total for meaningful ML
CASES = [
    # Original 11 cases
    ("CR-2026-BNG-001", "Cyber Crime & Online Fraud", "Whitefield Police Station", -3, "open", "forged biometric login, micro-lending extortion", ["Vikram Yadav"], ["K. S. Narayanan"], "FIR-045/BNG/2026", "IPC 420, IT Act 66D", "high", 45),
    ("CR-2026-BNG-002", "Cyber Crime & Online Fraud", "KR Puram Police Station", -8, "open", "wallet mule routing, call spoofing", ["Vikram Yadav"], ["K. S. Narayanan"], "FIR-052/BNG/2026", "IPC 419, IT Act 66C", "medium", 25),
    ("CR-2026-MYS-001", "Theft & Burglaries", "Devaraja Police Station", -6, "open", "late night lock break, scooter reconnaissance", ["Ramu Swamy", "Karthik Gowda"], ["Dr. Vinay Murthy"], "FIR-789/MYS/2026", "IPC 379, 457", "high", 60),
    ("CR-2026-MYS-002", "Theft & Burglaries", "Devaraja Police Station", -18, "closed", "repeat balcony entry, jewellery targeting", ["Ramu Swamy"], ["Dr. Vinay Murthy"], "FIR-790/MYS/2026", "IPC 380", "medium", 100),
    ("CR-2026-MNG-001", "Narcotics Smuggling Services", "Pandeshwar Police Station", -4, "open", "synthetic MDMA harbor handoff", ["Sayed Ibrahim"], ["Asha Rao"], "FIR-331/MNG/2026", "NDPS 21, 22", "critical", 15),
    ("CR-2026-BLG-001", "Smuggling & Excise Violations", "Khade Bazar Station", -10, "open", "forged inter-state clearance slips", ["Karthik Gowda"], ["Prakash Jain"], "FIR-204/BLG/2026", "Excise Act 32", "low", 40),
    ("CR-2026-BLR-001", "Illegal Mining Violations", "Rural Police Station", -13, "open", "night mineral transport convoy", ["Mohsin Pasha"], [], "FIR-611/BLR/2026", "MMDR Act 21", "high", 80),
    ("CR-2026-KLB-001", "Property Disputes", "Chowk Police Station", -15, "closed", "survey intimidation, prior offender density", ["Karthik Gowda"], [], "FIR-122/KLB/2026", "IPC 447, 506", "low", 100),
    ("CR-2026-HSN-001", "Domestic Violence", "City Police Station", -23, "open", "repeat household assault complaint", [], ["Latha Hegde"], "FIR-208/HSN/2026", "DV Act", "medium", 30),
    ("CR-2026-TMK-001", "Assault", "Town Police Station", -31, "closed", "industrial road altercation", [], [], "FIR-144/TMK/2026", "IPC 323", "medium", 100),
    ("CR-2026-DWD-001", "Theft & Burglaries", "Suburban Police Station", -35, "closed", "market yard attempted theft", ["Ramu Swamy"], [], "FIR-177/DWD/2026", "IPC 379", "low", 100),
]


def _generate_synthetic_cases():
    """Generate 49 additional synthetic cases spread across 12 months, 10 districts, 8 categories."""
    rng = random.Random(42)
    category_names = [c[0] for c in CATEGORIES]
    station_map = {loc[2]: loc[1] for loc in LOCATIONS}
    stations = list(station_map.keys())

    criminal_names = [c[0] for c in CRIMINALS]
    victim_names = [v[0] for v in VICTIMS]

    statuses = ["open", "open", "open", "closed", "investigating"]
    priorities = ["low", "medium", "medium", "high", "critical"]
    now = datetime.now()
    cases = []

    for i in range(49):
        cat = rng.choice(category_names)
        station = rng.choice(stations)
        district = station_map[station]
        days_ago = rng.randint(1, 365)
        status = rng.choice(statuses)
        priority = rng.choice(priorities)
        progress = rng.randint(0, 100) if status == "closed" else rng.randint(5, 80)
        n_criminals = rng.choices([0, 1, 2, 3], weights=[30, 40, 20, 10])[0]
        n_victims = rng.choices([0, 1, 2], weights=[40, 45, 15])[0]
        selected_criminals = rng.sample([c for c in criminal_names if c not in ["Ramu Swamy", "Vikram Yadav", "Sayed Ibrahim", "Karthik Gowda", "Mohsin Pasha"]], min(n_criminals, 55))
        selected_victims = rng.sample(victim_names, min(n_victims, 25))

        case_num = f"CR-2026-SYN-{i+1:03d}"
        fir_num = f"FIR-{rng.randint(200,999)}/SYN/2026"
        mo_options = [
            "night operation, mask used", "vehicle reconnaissance, parked getaway bike",
            "insider tip suspected", "repeated pattern across districts", "fake identity documents",
            "coordinated group activity", "electronic surveillance evasion", "cash-only transactions",
            "modified vehicle plates", "warehouse hideout used"
        ]
        mo_tags = ", ".join(rng.sample(mo_options, rng.randint(1, 3)))
        sections = rng.choice(["IPC 379, 457", "IPC 420, IT Act 66D", "NDPS 21", "IPC 323, 324", "MMDR Act 21", "DV Act", "IPC 447, 506", "Excise Act 32"])

        cases.append((case_num, cat, station, -days_ago, status, mo_tags, selected_criminals, selected_victims, fir_num, sections, priority, progress))
    return cases


ALL_CASES = CASES + _generate_synthetic_cases()


DEMO_NOTIFICATIONS = [
    # (sender_username, recipient_username_or_None, subject, type, category, title, message, priority, severity, status, case_no, fir_no, is_broadcast, hours_ago)
    ("SCRB-7740", "IO-3921", "Gang activity detected in Whitefield Sector-4", "intelligence_sharing", "intelligence_sharing", "Gang Activity Alert — Whitefield", "Recent analytics indicate repeated movement of suspects associated with CR-2026-BNG-001. Increase patrol frequency and verify CCTV feeds in Sector-4 between 22:00–04:00.", "high", "high", "unread", "CR-2026-BNG-001", None, False, 2),
    ("IO-3921", "SCRB-7740", "Evidence Uploaded for CR-2026-MYS-001", "case_update", "evidence_request", "CCTV Footage & Witness Statements Ready", "Digital CCTV footage from Devaraja Market Zone and three witness statements have been uploaded for CR-2026-MYS-001. Please review for pattern analysis.", "medium", "medium", "read", "CR-2026-MYS-001", "FIR-789/MYS/2026", False, 5),
    ("SP-0088", None, "Operation Night Shield — Statewide Directive", "emergency_broadcast", "emergency_broadcast", "Operation Night Shield Activated", "All officers are instructed to increase highway surveillance from 21:00 to 05:00 effective immediately. Refer to operational order KSP/2026/NS-041 for assignment details.", "critical", "critical", "unread", None, None, True, 8),
    ("admin", None, "Scheduled System Maintenance Notice", "system_notification", "system_notification", "System Maintenance — 23:30 to 00:30", "Platform maintenance is scheduled tonight between 23:30 and 00:30 IST. All active sessions will be preserved. AI inference services may be temporarily unavailable.", "low", "low", "read", None, None, True, 12),
    ("IO-3921", "SP-0088", "Request for Additional Cyber Forensic Personnel", "case_escalation", "case_escalation", "Cyber Forensic Support Required — CR-2026-BNG-001", "The investigation into CR-2026-BNG-001 requires dedicated cyber forensic support. Current evidence analysis has identified complex digital trails that need specialized extraction. Requesting immediate assignment of a cyber forensic unit.", "high", "high", "unread", "CR-2026-BNG-001", "FIR-045/BNG/2026", False, 3),
    ("SCRB-7740", "admin", "AI Hotspot Prediction Generated — 3 Emerging Zones", "intelligence_sharing", "intelligence_sharing", "Hotspot Predictions Ready for Review", "AI model has identified three emerging crime hotspots in Bengaluru Urban requiring review. Predictions are based on 31-feature LightGBM analysis. See dashboard for detailed overlay.", "medium", "medium", "acknowledged", None, None, False, 6),
    ("SP-0088", "IO-3921", "Arrest Warrant Approved — Sayed Ibrahim", "investigation_update", "investigation_update", "Arrest Warrant Issued", "The arrest warrant for Sayed Ibrahim (alias: Sayed) in connection with CR-2026-MNG-001 has been approved by the jurisdictional magistrate. Proceed with coordinated apprehension.", "critical", "critical", "unread", "CR-2026-MNG-001", "FIR-331/MNG/2026", False, 1),
    ("IO-3921", "SCRB-7740", "Suspect Movement Tracked — Mysuru Division", "intelligence_sharing", "intelligence_sharing", "Real-Time Suspect Tracking Update", "Vehicle registration KA-09-M-4412 linked to Vikram Yadav was flagged at KR Puram Transit Corridor at 14:32. CCTV capture forwarded. Requesting SCRB analysis of route patterns.", "high", "high", "read", "CR-2026-BNG-001", "FIR-052/BNG/2026", False, 10),
    ("SCRB-7740", "IO-3921", "Evidence Chain Verification Required", "evidence_request", "evidence_request", "Chain of Custody Verification — CR-2026-MYS-001", "Evidence packet for CR-2026-MYS-001 requires chain of custody verification. Physical evidence from Devaraja Market Zone must be cross-referenced with digital timestamps. Deadline: 48 hours.", "medium", "medium", "unread", "CR-2026-MYS-001", "FIR-789/MYS/2026", False, 4),
    ("IO-3921", None, "Narcotics Seizure Report — Mangaluru Harbor", "case_update", "case_update", "Seizure Report Filed", "Detailed narcotics seizure report for the Mangaluru Harbor operation has been compiled. 2.4 kg synthetic MDMA recovered. Forensic lab results pending.", "high", "high", "unread", "CR-2026-MNG-001", "FIR-331/MNG/2026", True, 7),
    ("SP-0088", "SCRB-7740", "Weekly Intelligence Brief — District Overview", "intelligence_sharing", "intelligence_sharing", "Weekly Intelligence Summary", "Weekly intelligence brief for all districts is now available. Key highlights: 3 new hotspots identified, 2 gang networks mapped, 15% reduction in property crimes in Mysuru division.", "low", "low", "read", None, None, False, 24),
    ("admin", "IO-3921", "Officer Badge Update", "administrative", "administrative", "Badge Configuration Updated", "Your officer badge profile has been updated with the latest certification. All access permissions have been synchronized.", "low", "low", "read", None, None, False, 48),
]


def seed() -> None:
    db = SessionLocal()
    try:
        role_objs = _seed_roles(db)
        user_objs = _seed_users(db, role_objs)
        officer_objs = _seed_officers(db, user_objs)
        category_objs = _seed_categories(db)
        location_objs = _seed_locations(db)
        criminal_objs = _seed_criminals(db)
        victim_objs = _seed_victims(db)
        _seed_cases_and_firs(db, category_objs, location_objs, criminal_objs, victim_objs, officer_objs)
        _seed_notifications(db, user_objs)
        db.commit()
        print("Seed complete. Prototype logins:")
        print("- admin / 564738")
        print("- SCRB-7740 / 123456")
        print("- IO-3921 / 456789")
        print("- SP-0088 / 987654")
    finally:
        db.close()


def _seed_roles(db):
    role_objs = {}
    for name in ROLES:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=f"{name} role")
            db.add(role)
            db.flush()
        role_objs[name] = role
    return role_objs


def _seed_users(db, role_objs):
    user_objs = {}
    for payload in DEMO_USERS:
        user = db.query(User).filter(User.username == payload["username"]).first()
        if not user:
            user = User(
                username=payload["username"],
                email=payload["email"],
                full_name=payload["full_name"],
                hashed_password=hash_password(payload["password"]),
                role_id=role_objs[payload["role_name"]].id,
                district=payload.get("district"),
                station=payload.get("station"),
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.hashed_password = hash_password(payload["password"])
            db.flush()
        user_objs[payload["username"]] = user
    return user_objs


def _seed_officers(db, user_objs):
    officers = {}
    for payload in DEMO_USERS:
        badge = payload.get("badge_number")
        if not badge:
            continue
        officer = db.query(Officer).filter(Officer.badge_number == badge).first()
        if not officer:
            officer = Officer(
                user_id=user_objs[payload["username"]].id,
                badge_number=badge,
                name=payload["full_name"],
                rank=payload.get("rank"),
                district=payload.get("district") or "State HQ",
                station=payload.get("station") or "KSP HQ",
            )
            db.add(officer)
            db.flush()
        officers[badge] = officer
    return officers


def _seed_categories(db):
    categories = {}
    for name, section_code, severity in CATEGORIES:
        category = db.query(CrimeCategory).filter(CrimeCategory.name == name).first()
        if not category:
            category = CrimeCategory(name=name, section_code=section_code, severity=severity)
            db.add(category)
            db.flush()
        categories[name] = category
    return categories


def _seed_locations(db):
    locations = {}
    for address, district, station, lat, lng, pincode in LOCATIONS:
        location = db.query(Location).filter(Location.station == station, Location.address == address).first()
        if not location:
            location = Location(address=address, district=district, station=station, latitude=lat, longitude=lng, pincode=pincode)
            db.add(location)
            db.flush()
        locations[station] = location
    return locations


def _seed_criminals(db):
    criminals = {}
    for full_name, aliases, dob, gender, marks, mo, status in CRIMINALS:
        criminal = db.query(Criminal).filter(Criminal.full_name == full_name).first()
        if not criminal:
            criminal = Criminal(
                full_name=full_name,
                aliases=aliases,
                date_of_birth=dob,
                gender=gender,
                identifying_marks=marks,
                mo_summary=mo,
                status=status,
            )
            db.add(criminal)
            db.flush()
        criminals[full_name] = criminal
    return criminals


def _seed_victims(db):
    victims = {}
    for full_name, contact, address, gender, age, statement in VICTIMS:
        victim = db.query(Victim).filter(Victim.full_name == full_name, Victim.contact_number == contact).first()
        if not victim:
            victim = Victim(full_name=full_name, contact_number=contact, address=address, gender=gender, age=age, statement=statement)
            db.add(victim)
            db.flush()
        victims[full_name] = victim
    return victims


def _seed_cases_and_firs(db, categories, locations, criminals, victims, officers):
    investigator = officers.get("IO-3921") or next(iter(officers.values()), None)
    now = datetime.now()
    for item in ALL_CASES:
        case_number, category_name, station, days, status, mo_tags, criminal_names, victim_names, fir_number, sections, priority, progress = item
        crime = db.query(CrimeCase).filter(CrimeCase.case_number == case_number).first()
        if not crime:
            crime = CrimeCase(
                case_number=case_number,
                category_id=categories[category_name].id,
                location_id=locations[station].id,
                occurred_at=now + timedelta(days=days),
                description=f"{category_name} reported at {locations[station].address}",
                mo_tags=mo_tags,
                status=status,
                priority=priority,
                progress=progress,
                assigned_officer_id=investigator.id if investigator else None
            )
            db.add(crime)
            db.flush()
        else:
            crime.priority = priority
            crime.progress = progress
            if not crime.assigned_officer_id and investigator:
                crime.assigned_officer_id = investigator.id
            db.flush()

        fir = db.query(FIR).filter(FIR.fir_number == fir_number).first()
        if not fir:
            import json
            fir = FIR(
                fir_number=fir_number,
                crime_case_id=crime.id,
                investigating_officer_id=investigator.id if investigator else None,
                complainant_name=victim_names[0] if victim_names else "State Complainant",
                complainant_contact=victims[victim_names[0]].contact_number if victim_names else None,
                sections=sections,
                status="registered" if status == "open" else "closed",
                narrative=f"Backend-seeded FIR for {case_number}; derived from the Police FIR ER model.",
                attachments=json.dumps([
                    {"name": f"complaint_copy_{case_number}.pdf", "size": 154200},
                    {"name": f"spot_mahazar_{case_number}.pdf", "size": 284100}
                ])
            )
            db.add(fir)
            db.flush()

        for criminal_name in criminal_names:
            criminal = criminals[criminal_name]
            exists = db.query(FIRCriminalLink).filter(FIRCriminalLink.fir_id == fir.id, FIRCriminalLink.criminal_id == criminal.id).first()
            if not exists:
                db.add(FIRCriminalLink(fir_id=fir.id, criminal_id=criminal.id, role="accused"))

        for victim_name in victim_names:
            victim = victims[victim_name]
            exists = db.query(FIRVictimLink).filter(FIRVictimLink.fir_id == fir.id, FIRVictimLink.victim_id == victim.id).first()
            if not exists:
                db.add(FIRVictimLink(fir_id=fir.id, victim_id=victim.id))

        evidence_exists = db.query(Evidence).filter(Evidence.case_id == crime.id).first()
        if not evidence_exists:
            # Determine evidence type and description based on category
            if "Cyber" in category_name:
                ev_type = "digital"
                ev_title = f"Digital Forensics — {case_number}"
                ev_desc = f"Digital evidence including device images, network logs, and transaction records for {case_number}. Captured during initial response on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."
            elif "Narcotics" in category_name or "Smuggling" in category_name:
                ev_type = "physical"
                ev_title = f"Narcotics Seizure Kit — {case_number}"
                ev_desc = f"Physical evidence including seized substances, packaging materials, and transport vehicle documentation for {case_number}. Collected at scene on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."
            elif "Theft" in category_name or "Burglar" in category_name:
                ev_type = "physical"
                ev_title = f"Burglary Evidence Packet — {case_number}"
                ev_desc = f"Physical evidence including tool marks, fingerprints, and stolen property inventory for {case_number}. Secured from crime scene on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."
            elif "Assault" in category_name:
                ev_type = "document"
                ev_title = f"Assault Case Documentation — {case_number}"
                ev_desc = f"Medical reports, witness statements, and scene photographs for assault case {case_number}. Compiled on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."
            elif "Mining" in category_name:
                ev_type = "document"
                ev_title = f"Mining Violation Records — {case_number}"
                ev_desc = f"Satellite imagery, transit manifests, and forged permits for illegal mining case {case_number}. Documented on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."
            elif "Domestic" in category_name:
                ev_type = "document"
                ev_title = f"DV Case Evidence — {case_number}"
                ev_desc = f"Medical examination reports, complaint statements, and photographic evidence for {case_number}. Filed on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."
            else:
                ev_type = "document"
                ev_title = f"Case Evidence — {case_number}"
                ev_desc = f"Supporting documentation and evidence for {case_number}. Collected on {crime.occurred_at.strftime('%Y-%m-%d') if crime.occurred_at else 'N/A'}."

            ev_status = "Analyzed" if status == "closed" else "Under Analysis" if progress > 30 else "Pending"
            badge = investigator.badge_number if investigator else "SCRB"
            officer_name = investigator.name if investigator else "SCRB Analyst"

            evidence = Evidence(
                case_id=crime.id,
                title=ev_title,
                evidence_type=ev_type,
                description=ev_desc,
                created_by=officer_name,
                status=ev_status,
                storage_path=f"/evidence/{crime.id}/{ev_type}_packet",
            )
            db.add(evidence)
            db.flush()

            # Chain of custody: registration
            db.add(ChainOfCustody(
                evidence_id=evidence.id,
                from_user=investigator.user_id if investigator else None,
                to_user=investigator.user_id if investigator else None,
                action="Evidence Registered",
                location=locations[station].address if station in locations else "Unknown",
                remarks=f"Evidence logged for case {case_number}",
            ))

            # Chain of custody: analysis started (if evidence is under analysis or beyond)
            if progress > 30:
                db.add(ChainOfCustody(
                    evidence_id=evidence.id,
                    from_user=investigator.user_id if investigator else None,
                    to_user=investigator.user_id if investigator else None,
                    action="Forensic Analysis Initiated",
                    location="Forensic Lab",
                    remarks="Evidence submitted for forensic examination",
                ))

            # Chain of custody: analyzed (if case is closed)
            if status == "closed":
                db.add(ChainOfCustody(
                    evidence_id=evidence.id,
                    from_user=investigator.user_id if investigator else None,
                    to_user=investigator.user_id if investigator else None,
                    action="Analysis Completed",
                    location="Forensic Lab",
                    remarks="Forensic analysis complete — results filed with charge sheet",
                ))


def _seed_notifications(db, user_objs):
    """Seed inter-station communication notifications."""
    existing = db.query(Notification).count()
    if existing > 0:
        return

    now = datetime.now()
    for entry in DEMO_NOTIFICATIONS:
        sender_username, recipient_username, subject, ntype, category, title, message, priority, severity, status, case_no, fir_no, is_broadcast, hours_ago = entry

        sender = user_objs.get(sender_username)
        recipient = user_objs.get(recipient_username) if recipient_username else None

        notif = Notification(
            user_id=recipient.id if recipient else None,
            sender_id=sender.id if sender else None,
            subject=subject,
            notification_type=ntype,
            category=category,
            title=title,
            message=message,
            priority=priority,
            severity=severity,
            status=status,
            related_case_number=case_no,
            related_fir_number=fir_no,
            is_broadcast=is_broadcast,
            is_read=(status != "unread"),
            is_dismissed=False,
            created_at=now - timedelta(hours=hours_ago),
        )
        if status == "read":
            notif.read_at = now - timedelta(hours=max(0, hours_ago - 1))
        elif status == "acknowledged":
            notif.read_at = now - timedelta(hours=max(0, hours_ago - 1))
            notif.acknowledged_at = now - timedelta(hours=max(0, hours_ago - 2))

        db.add(notif)

    db.flush()
    print(f"Seeded {len(DEMO_NOTIFICATIONS)} demo notifications")


if __name__ == "__main__":
    seed()

