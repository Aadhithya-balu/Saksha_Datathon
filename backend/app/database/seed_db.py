"""Seed roles, operators, and an ER-shaped prototype crime dataset.

Expanded to cover all 31 Karnataka districts with realistic police stations,
officers, victims, and cases for a production-grade demo.

Issue #164: Every record created by this seed script is tagged with
``dataset_provenance='demo'`` so operational intelligence pipelines can
clearly distinguish seeded demonstration data from live or migrated records.
"""
import random
from datetime import date, datetime, timedelta, time

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
from app.models.intervention import Intervention

# Issue #164: canonical provenance tag for seed data
_SEED_PROVENANCE = "demo"

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

# ---------------------------------------------------------------------------
# LOCATIONS — 68 stations across all 31 Karnataka districts
# Organized by region: North, Central, South, Coastal
# ---------------------------------------------------------------------------
LOCATIONS = [
    # === NORTH KARNATAKA ===
    # Belagavi
    ("Khade Bazar Checkpoint", "Belagavi", "Khade Bazar Station", 15.8497, 74.4977, "590001"),
    ("Camp Area Patrol", "Belagavi", "Camp Police Station", 15.8625, 74.5050, "590006"),
    ("Tilakwadi Beat", "Belagavi", "Tilakwadi Police Station", 15.8380, 74.4780, "590009"),
    # Dharwad
    ("Dharwad Market Yard", "Dharwad", "Suburban Police Station", 15.4589, 75.0078, "580001"),
    ("Hubli Traffic Island", "Dharwad", "Hubli City Police Station", 15.3647, 75.1240, "580002"),
    # Gadag
    ("Gadag Town Center", "Gadag", "Gadag Town Police Station", 15.4289, 75.6270, "582101"),
    ("Betageri Cross", "Gadag", "Betageri Police Station", 15.4450, 75.6100, "582102"),
    # Haveri
    ("Haveri Bus Stand Area", "Haveri", "Haveri Town Police Station", 14.7936, 75.4050, "581110"),
    ("Ranebennur Cross", "Haveri", "Ranebennur Police Station", 14.6113, 75.6210, "581115"),
    # Bagalkote
    ("Bagalkote Main Road", "Bagalkote", "Bagalkote Town Police Station", 16.1800, 75.6930, "587101"),
    ("Jamakhandi Station Road", "Bagalkote", "Jamakhandi Police Station", 16.5360, 75.2930, "587102"),
    # Vijayapura (Bijapur)
    ("Vijayapura Fort Area", "Vijayapura", "Vijayapura City Police Station", 16.8300, 75.7100, "586101"),
    ("Indi Town Center", "Vijayapura", "Indi Police Station", 17.1800, 75.9500, "586102"),
    # Kalaburagi
    ("Chowk Survey Layout", "Kalaburagi", "Chowk Police Station", 17.3297, 76.8343, "585101"),
    ("Gulbarga University Road", "Kalaburagi", "Afzalpur Road Police Station", 17.3300, 76.8500, "585102"),
    # Yadagir
    ("Yadagir Town Center", "Yadagir", "Yadagir Town Police Station", 16.7700, 77.0400, "585201"),
    # Bidar
    ("Bidar Fort Road", "Bidar", "Bidar Town Police Station", 17.9100, 77.5200, "585101"),
    ("Homnabad Cross", "Bidar", "Homnabad Police Station", 17.7700, 77.1300, "585102"),
    # Koppal
    ("Koppal Town Center", "Koppal", "Koppal Town Police Station", 15.3500, 76.1300, "583101"),
    ("Gangavathi Road", "Koppal", "Gangavathi Police Station", 15.4300, 76.5300, "583102"),

    # === CENTRAL KARNATAKA ===
    # Bengaluru Urban
    ("Whitefield Cyber Cell Beat", "Bengaluru Urban", "Whitefield Police Station", 12.9698, 77.7500, "560066"),
    ("KR Puram Transit Corridor", "Bengaluru Urban", "KR Puram Police Station", 13.0056, 77.6880, "560036"),
    ("Koramangala Layout", "Bengaluru Urban", "Koramangala Police Station", 12.9352, 77.6245, "560034"),
    ("HSR Layout Beat", "Bengaluru Urban", "HSR Layout Police Station", 12.9116, 77.6389, "560102"),
    ("Jayanagar 4th Block", "Bengaluru Urban", "Jayanagar Police Station", 12.9260, 77.5830, "560041"),
    # Bengaluru Rural
    ("Devanahalli Checkpost", "Bengaluru Rural", "Devanahalli Police Station", 13.2480, 77.7110, "562110"),
    ("Hoskote Junction", "Bengaluru Rural", "Hoskote Police Station", 13.0700, 77.7800, "562114"),
    # Tumkuru
    ("Tumkuru Industrial Road", "Tumkuru", "Town Police Station", 13.3379, 77.1173, "572101"),
    ("Tiptur Market Area", "Tumkuru", "Tiptur Police Station", 13.2600, 76.4800, "572102"),
    # Kolar
    ("Kolar Gold Fields Road", "Kolar", "Kolar Town Police Station", 13.1350, 78.1300, "563101"),
    ("Bangarapet Station Road", "Kolar", "Bangarapet Police Station", 12.9900, 78.1800, "563102"),
    # Chikkaballapura
    ("Chikkaballapura Town", "Chikkaballapura", "Chikkaballapura Town Police Station", 13.4300, 77.7200, "562101"),
    ("Gauribidanur Cross", "Chikkaballapura", "Gauribidanur Police Station", 13.6100, 77.5100, "562102"),
    # Ramanagara
    ("Ramanagara Town Center", "Ramanagara", "Ramanagara Town Police Station", 12.7200, 77.2800, "562109"),
    ("Channapatna Bus Stand", "Ramanagara", "Channapatna Police Station", 12.6500, 77.2100, "562106"),
    # Hassan
    ("Hassan City East", "Hassan", "City Police Station", 13.0641, 76.1030, "573201"),
    ("Arsikere Town Road", "Hassan", "Arsikere Police Station", 13.3100, 76.2500, "573102"),
    # Mandya
    ("Mandya Town Center", "Mandya", "Mandya Town Police Station", 12.5200, 76.9000, "571401"),
    ("Mysuru-Mandya Highway", "Mandya", "Srirangapatna Police Station", 12.4200, 76.6900, "571402"),
    # Chitradurga
    ("Chitradurga Fort Area", "Chitradurga", "Chitradurga Town Police Station", 14.2300, 76.4000, "577501"),
    ("Hiriyur Junction", "Chitradurga", "Hiriyur Police Station", 14.0800, 76.5400, "577502"),

    # === SOUTH KARNATAKA ===
    # Mysuru
    ("Devaraja Market Zone", "Mysuru", "Devaraja Police Station", 12.2958, 76.6394, "570001"),
    ("Nazar Mohalla Beat", "Mysuru", "Nazarbad Police Station", 12.3200, 76.6500, "570010"),
    ("Vani Vilas Mohalla", "Mysuru", "Vani Vilas Mohalla Police Station", 12.3100, 76.6200, "570017"),
    # Chamarajanagar
    ("Chamarajanagar Town", "Chamarajanagar", "Chamarajanagar Town Police Station", 11.9200, 76.9400, "571313"),
    ("Gundlupet Junction", "Chamarajanagar", "Gundlupet Police Station", 11.8100, 76.6900, "571312"),
    # Kodagu (Coorg)
    ("Madikeri Town Center", "Kodagu", "Madikeri Town Police Station", 12.4200, 75.7400, "571201"),
    ("Virajpet Cross Road", "Kodagu", "Virajpet Police Station", 12.2000, 75.8000, "571202"),
    # Davanagere
    ("Davanagere Market Road", "Davanagere", "Davanagere Town Police Station", 14.4644, 75.9218, "577001"),
    ("Harpanahalli Junction", "Davanagere", "Harpanahalli Police Station", 14.5100, 75.9900, "577002"),
    # Shimoga
    ("Shimoga City Center", "Shimoga", "Shimoga Town Police Station", 13.9300, 75.5600, "577201"),
    ("Sagara Main Road", "Shimoga", "Sagara Police Station", 14.1600, 75.0300, "577202"),
    ("Tirthahalli Cross", "Shimoga", "Tirthahalli Police Station", 13.6900, 75.2400, "577203"),
    # Chikkamagaluru
    ("Chikkamagaluru Town", "Chikkamagaluru", "Chikkamagaluru Town Police Station", 13.3200, 75.7800, "577101"),
    ("Kadur Junction", "Chikkamagaluru", "Kadur Police Station", 13.5500, 76.0100, "577102"),
    # Ballari
    ("Ballari Mines Sector B", "Ballari", "Rural Police Station", 15.1394, 76.9214, "583101"),
    ("Bellary City Center", "Ballari", "City Police Station", 15.1400, 76.9100, "583102"),
    # Raichur
    ("Raichur Town Center", "Raichur", "Raichur Town Police Station", 16.2100, 77.3500, "584101"),
    ("Yadgir Road Junction", "Raichur", "Mantralayam Road Police Station", 16.1900, 77.3700, "584102"),
    # Vijayanagara (Hospet)
    ("Hospet Town Center", "Vijayanagara", "Hospet Town Police Station", 15.2700, 76.4600, "583101"),
    ("Bellary-Hospet Road", "Vijayanagara", "Sandur Police Station", 15.2500, 76.5500, "583102"),

    # === COASTAL KARNATAKA ===
    # Dakshina Kannada (Mangaluru)
    ("Harbor Gate A", "Dakshina Kannada", "Pandeshwar Police Station", 12.9050, 74.8350, "575001"),
    ("Surathkal Beach Road", "Dakshina Kannada", "Surathkal Police Station", 12.9800, 74.8600, "575002"),
    ("Puttur Town Center", "Dakshina Kannada", "Puttur Police Station", 12.7600, 75.2500, "574201"),
    # Udupi
    ("Udupi Krishna Math Road", "Udupi", "Udupi Town Police Station", 13.3400, 74.7400, "576101"),
    ("Kapu Beach Junction", "Udupi", "Kapu Police Station", 13.3800, 74.6800, "576102"),
    # Uttara Kannada (Karwar)
    ("Karwar Port Road", "Uttara Kannada", "Karwar Town Police Station", 14.8100, 74.1300, "581301"),
    ("Sirsi Town Center", "Uttara Kannada", "Sirsi Police Station", 14.6200, 74.8300, "581302"),
    ("Yellapur Junction", "Uttara Kannada", "Yellapur Police Station", 14.9700, 74.7000, "581303"),
]

# ---------------------------------------------------------------------------
# STANDALONE_OFFICERS — 30 officers deployed across Karnataka districts
# These officers do NOT have user login accounts; they appear in the officer
# directory and are assigned to cases for realistic distribution.
# ---------------------------------------------------------------------------
STANDALONE_OFFICERS = [
    # North Karnataka
    {"badge_number": "IO-1247", "name": "Inspector Virupakshi Hallur", "rank": "Inspector", "district": "Belagavi", "station": "Khade Bazar Station", "designation": "SHO", "phone": "+91 94480 12001", "email": "virupakshi.h@ksp.gov.in"},
    {"badge_number": "SI-3382", "name": "Sub-Inspector Muttanna Goudar", "rank": "Sub-Inspector", "district": "Belagavi", "station": "Camp Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12002", "email": "muttanna.g@ksp.gov.in"},
    {"badge_number": "IO-5501", "name": "Inspector Manoj Biradar", "rank": "Inspector", "district": "Dharwad", "station": "Hubli City Police Station", "designation": "SHO", "phone": "+91 94480 12003", "email": "manoj.b@ksp.gov.in"},
    {"badge_number": "SI-4419", "name": "Sub-Inspector Fakirappa Doddamani", "rank": "Sub-Inspector", "district": "Kalaburagi", "station": "Chowk Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12004", "email": "fakirappa.d@ksp.gov.in"},
    {"badge_number": "IO-6623", "name": "Inspector Basavaraj Kolkar", "rank": "Inspector", "district": "Vijayapura", "station": "Vijayapura City Police Station", "designation": "SHO", "phone": "+91 94480 12005", "email": "basavaraj.k@ksp.gov.in"},
    {"badge_number": "SI-2290", "name": "Sub-Inspector Sharanabasappa Deshpande", "rank": "Sub-Inspector", "district": "Gadag", "station": "Gadag Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12006", "email": "sharanabasappa.d@ksp.gov.in"},
    {"badge_number": "IO-7734", "name": "Inspector Raju Patil", "rank": "Inspector", "district": "Bagalkote", "station": "Bagalkote Town Police Station", "designation": "SHO", "phone": "+91 94480 12007", "email": "raju.p@ksp.gov.in"},
    {"badge_number": "SI-8812", "name": "Sub-Inspector Nagesh Kori", "rank": "Sub-Inspector", "district": "Haveri", "station": "Haveri Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12008", "email": "nagesh.k@ksp.gov.in"},
    {"badge_number": "IO-9945", "name": "Inspector Farooq Nadaf", "rank": "Inspector", "district": "Bidar", "station": "Bidar Town Police Station", "designation": "SHO", "phone": "+91 94480 12009", "email": "farooq.n@ksp.gov.in"},
    {"badge_number": "SI-1156", "name": "Sub-Inspector Venkatesh Kulkarni", "rank": "Sub-Inspector", "district": "Yadagir", "station": "Yadagir Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12010", "email": "venkatesh.k@ksp.gov.in"},

    # Central Karnataka
    {"badge_number": "IO-2267", "name": "Inspector Kavitha Prasad", "rank": "Inspector", "district": "Bengaluru Urban", "station": "Koramangala Police Station", "designation": "SHO", "phone": "+91 94480 12011", "email": "kavitha.p@ksp.gov.in"},
    {"badge_number": "SI-3378", "name": "Sub-Inspector Deepak Sharma", "rank": "Sub-Inspector", "district": "Bengaluru Urban", "station": "HSR Layout Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12012", "email": "deepak.s@ksp.gov.in"},
    {"badge_number": "IO-4489", "name": "Inspector Suresh Babu", "rank": "Inspector", "district": "Bengaluru Urban", "station": "Jayanagar Police Station", "designation": "SHO", "phone": "+91 94480 12013", "email": "suresh.b@ksp.gov.in"},
    {"badge_number": "SI-5590", "name": "Sub-Inspector Lakshmi Devi", "rank": "Sub-Inspector", "district": "Bengaluru Rural", "station": "Devanahalli Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12014", "email": "lakshmi.d@ksp.gov.in"},
    {"badge_number": "IO-6601", "name": "Inspector Ganesh Haldipur", "rank": "Inspector", "district": "Tumkuru", "station": "Town Police Station", "designation": "SHO", "phone": "+91 94480 12015", "email": "ganesh.h@ksp.gov.in"},
    {"badge_number": "SI-7712", "name": "Sub-Inspector Anitha Kulkarni", "rank": "Sub-Inspector", "district": "Kolar", "station": "Kolar Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12016", "email": "anitha.k@ksp.gov.in"},
    {"badge_number": "IO-8823", "name": "Inspector Mohammed Irfan", "rank": "Inspector", "district": "Hassan", "station": "City Police Station", "designation": "SHO", "phone": "+91 94480 12017", "email": "mohammed.i@ksp.gov.in"},
    {"badge_number": "SI-9934", "name": "Sub-Inspector Prakash Naik", "rank": "Sub-Inspector", "district": "Mandya", "station": "Mandya Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12018", "email": "prakash.n@ksp.gov.in"},
    {"badge_number": "IO-1045", "name": "Inspector Ravi Shankar Bhat", "rank": "Inspector", "district": "Chitradurga", "station": "Chitradurga Town Police Station", "designation": "SHO", "phone": "+91 94480 12019", "email": "ravishankar.b@ksp.gov.in"},
    {"badge_number": "SI-2156", "name": "Sub-Inspector Yashoda Patil", "rank": "Sub-Inspector", "district": "Ramanagara", "station": "Ramanagara Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12020", "email": "yashoda.p@ksp.gov.in"},

    # South Karnataka
    {"badge_number": "IO-3267", "name": "Inspector Bharath Gowda", "rank": "Inspector", "district": "Mysuru", "station": "Nazarbad Police Station", "designation": "SHO", "phone": "+91 94480 12021", "email": "bharath.g@ksp.gov.in"},
    {"badge_number": "SI-4378", "name": "Sub-Inspector Pushpa Lakshmi", "rank": "Sub-Inspector", "district": "Chamarajanagar", "station": "Chamarajanagar Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12022", "email": "pushpa.l@ksp.gov.in"},
    {"badge_number": "IO-5489", "name": "Inspector Kiran Bhat", "rank": "Inspector", "district": "Kodagu", "station": "Madikeri Town Police Station", "designation": "SHO", "phone": "+91 94480 12023", "email": "kiran.b@ksp.gov.in"},
    {"badge_number": "SI-6590", "name": "Sub-Inspector Yogesh Shetty", "rank": "Sub-Inspector", "district": "Shimoga", "station": "Shimoga Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12024", "email": "yogesh.s@ksp.gov.in"},
    {"badge_number": "IO-7601", "name": "Inspector Santosh Mudiraj", "rank": "Inspector", "district": "Davanagere", "station": "Davanagere Town Police Station", "designation": "SHO", "phone": "+91 94480 12025", "email": "santosh.m@ksp.gov.in"},
    {"badge_number": "SI-8712", "name": "Sub-Inspector Vinayak Kulkarni", "rank": "Sub-Inspector", "district": "Chikkamagaluru", "station": "Chikkamagaluru Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12026", "email": "vinayak.k@ksp.gov.in"},

    # Coastal Karnataka
    {"badge_number": "IO-9823", "name": "Inspector Irfan Hassan", "rank": "Inspector", "district": "Dakshina Kannada", "station": "Pandeshwar Police Station", "designation": "SHO", "phone": "+91 94480 12027", "email": "irfan.h@ksp.gov.in"},
    {"badge_number": "SI-0934", "name": "Sub-Inspector Nasir Shaikh", "rank": "Sub-Inspector", "district": "Dakshina Kannada", "station": "Surathkal Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12028", "email": "nasir.s@ksp.gov.in"},
    {"badge_number": "IO-1046", "name": "Inspector Sameer Patel", "rank": "Inspector", "district": "Udupi", "station": "Udupi Town Police Station", "designation": "SHO", "phone": "+91 94480 12029", "email": "sameer.p@ksp.gov.in"},
    {"badge_number": "SI-2157", "name": "Sub-Inspector Lokesh Biradar", "rank": "Sub-Inspector", "district": "Uttara Kannada", "station": "Karwar Town Police Station", "designation": "Investigating Officer", "phone": "+91 94480 12030", "email": "lokesh.b@ksp.gov.in"},
]

# ---------------------------------------------------------------------------
# CRIMINALS — 60 profiles for ML training
# ---------------------------------------------------------------------------
CRIMINALS = [
    ("Ramu Swamy", "Kodaikanal Ramu", date(1982, 4, 12), "Male", "Scar near left eyebrow", "Night residential lock-break burglaries using scooter reconnaissance", "at_large"),
    ("Vikram Yadav", "Vicky", date(1990, 11, 7), "Male", "Spectacles, gold ring", "Money mule coordinator for app-based cyber extortion", "at_large"),
    ("Sayed Ibrahim", "Sayed", date(1985, 2, 22), "Male", "Tattoo on right wrist", "Port logistics support for synthetic drug consignments", "at_large"),
    ("Karthik Gowda", "Gowda", date(1988, 8, 3), "Male", "Thick moustache", "Forgery and property document intimidation", "arrested"),
    ("Mohsin Pasha", "Pasha", date(1987, 1, 19), "Male", "Burn mark on forearm", "Illegal mineral transport and forged transit slips", "at_large"),
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

# ---------------------------------------------------------------------------
# VICTIMS — 40 victim/witness profiles across all regions
# ---------------------------------------------------------------------------
VICTIMS = [
    # North Karnataka
    ("Prakash Jain", "+91 98800 00004", "Belagavi", "Male", 41, "Reported forged excise transport documents."),
    ("Shobha Patil", "+91 98800 00010", "Belagavi", "Female", 35, "Received threatening calls for loan recovery."),
    ("Bharat Hegde", "+91 98800 00017", "Belagavi", "Male", 43, "ATM card cloned, account drained."),
    ("Pradeep Naik", "+91 98800 00013", "Dharwad", "Male", 37, "Shop broken into, cash and electronics stolen."),
    ("Gopal Krishna", "+91 98800 00022", "Dharwad", "Male", 45, "Property dispute turned violent."),
    ("Sarojini Bhat", "+91 98800 00026", "Gadag", "Female", 38, "Gold ornaments stolen during house break-in."),
    ("Mahantesh Patil", "+91 98800 00027", "Bagalkote", "Male", 52, "Agricultural land documents forged."),
    ("Kavita Banakar", "+91 98800 00028", "Haveri", "Female", 29, "Stalked and threatened over property dispute."),
    ("Ismail Nadaf", "+91 98800 00029", "Kalaburagi", "Male", 47, "Illegal mining near farmland reported."),

    # Central Karnataka
    ("K. S. Narayanan", "+91 98800 00001", "Bengaluru Urban", "Male", 52, "Reported biometric face ID bypass and loan extortion."),
    ("Sunita Devi", "+91 98800 00006", "Bengaluru Urban", "Female", 38, "Lost savings in online investment scam."),
    ("Dinesh Rao", "+91 98800 00019", "Bengaluru Urban", "Male", 34, "Phishing email led to bank account compromise."),
    ("Anupama Sharma", "+91 98800 00030", "Bengaluru Urban", "Female", 26, "Cyber stalking via social media, threats received."),
    ("Vijaya Kumari", "+91 98800 00031", "Bengaluru Rural", "Female", 55, "Retirement savings stolen via fake investment app."),
    ("Nagaraj Shetty", "+91 98800 00011", "Tumkuru", "Male", 60, "Property encroachment with threat of violence."),
    ("Eshwarappa", "+91 98800 00020", "Tumkuru", "Male", 58, "Farmland encroached by mining operators."),
    ("Chandrakala Devi", "+91 98800 00032", "Kolar", "Female", 49, "Gold chain snatched near temple."),
    ("Ramesh Gowda", "+91 98800 00033", "Hassan", "Male", 44, "Property forged by relatives, dispute ongoing."),
    ("Hema Malini", "+91 98800 00023", "Hassan", "Female", 52, "Jewellery stolen during house burglary."),
    ("Suma B", "+91 98800 00014", "Hassan", "Female", 28, "Stalked and harassed online via social media."),
    ("Shashikala Devi", "+91 98800 00034", "Mandya", "Female", 41, "Domestic violence case, multiple complaints filed."),
    ("Vasanth Kumar", "+91 98800 00035", "Chitradurga", "Male", 50, "Illegal quarry operations on private land."),

    # South Karnataka
    ("Dr. Vinay Murthy", "+91 98800 00002", "Mysuru", "Male", 46, "Reported night burglary and missing jewellery."),
    ("Mohan Krishna", "+91 98800 00007", "Mysuru", "Male", 55, "Vehicle stolen from parking lot near market."),
    ("Chitra K", "+91 98800 00018", "Mysuru", "Female", 39, "Fake police impersonator demanded bribe."),
    ("Jyothi Lingegowda", "+91 98800 00025", "Mysuru", "Female", 36, "Cyber fraud victim, lost retirement savings."),
    ("Manjula Devi", "+91 98800 00036", "Chamarajanagar", "Female", 33, "Assaulted during land boundary dispute."),
    ("Kaveri Poojary", "+91 98800 00037", "Kodagu", "Female", 29, "Coffee estate theft, equipment missing."),
    ("Arun Kumar", "+91 98800 00038", "Shimoga", "Male", 42, "Timber smuggling reported near forest boundary."),
    ("Padmavathi", "+91 98800 00039", "Davanagere", "Female", 37, "Gold chain snatched at bus stand."),
    ("Girijeshwar Rao", "+91 98800 00015", "Ballari", "Male", 50, "Illegal mining on ancestral land reported."),
    ("Rajendra Prasad", "+91 98800 00009", "Ballari", "Male", 48, "Land documents forged by fraudsters."),

    # Coastal Karnataka
    ("Asha Rao", "+91 98800 00003", "Dakshina Kannada", "Female", 33, "Witnessed cargo handoff near harbor gate."),
    ("Fathima Begum", "+91 98800 00008", "Dakshina Kannada", "Female", 42, "Gold chain snatched at traffic signal."),
    ("Ayesha Parveen", "+91 98800 00016", "Dakshina Kannada", "Female", 31, "Hawala transfer scam victim."),
    ("Irfan Ahmed", "+91 98800 00024", "Dakshina Kannada", "Male", 30, "Assaulted during road rage incident."),
    ("Sunanda Poojary", "+91 98800 00040", "Udupi", "Female", 45, "Fish export business fraud, money lost."),
    ("Rajesh Kharvi", "+91 98800 00041", "Uttara Kannada", "Male", 48, "Boat and fishing equipment stolen."),
]

# ---------------------------------------------------------------------------
# CASES — 75 hand-crafted cases spread across all districts and officers
# Format: (case_number, category, station, days_ago, status, mo_tags,
#          [criminal_names], [victim_names], fir_number, sections, priority, progress)
# ---------------------------------------------------------------------------
CASES = [
    # === NORTH KARNATAKA ===
    ("CR-2026-BLG-001", "Smuggling & Excise Violations", "Khade Bazar Station", -10, "open", "forged inter-state clearance slips", ["Karthik Gowda"], ["Prakash Jain"], "FIR-204/BLG/2026", "Excise Act 32", "low", 40),
    ("CR-2026-BLG-002", "Theft & Burglaries", "Camp Police Station", -15, "open", "night residential break-in, crowbar used", ["Ramu Swamy"], ["Bharat Hegde"], "FIR-205/BLG/2026", "IPC 379, 457", "medium", 25),
    ("CR-2026-BLG-003", "Cyber Crime & Online Fraud", "Tilakwadi Police Station", -7, "open", "fake banking portal phishing", ["Prasad Shenoy"], ["Shobha Patil"], "FIR-206/BLG/2026", "IPC 420, IT Act 66D", "high", 15),
    ("CR-2026-DWD-001", "Theft & Burglaries", "Suburban Police Station", -35, "closed", "market yard attempted theft", ["Ramu Swamy"], ["Pradeep Naik"], "FIR-177/DWD/2026", "IPC 379", "low", 100),
    ("CR-2026-DWD-002", "Narcotics Smuggling Services", "Hubli City Police Station", -5, "open", "interstate drug courier via bus terminal", ["Zaheer Ahmed"], [], "FIR-178/DWD/2026", "NDPS 21, 22", "critical", 10),
    ("CR-2026-GDG-001", "Property Disputes", "Gadag Town Police Station", -22, "investigating", "forged property deed, witness intimidation", ["Mahesh Jain"], ["Sarojini Bhat"], "FIR-301/GDG/2026", "IPC 447, 506", "medium", 45),
    ("CR-2026-BGT-001", "Assault", "Bagalkote Town Police Station", -18, "open", "road rage assault near bus stand", ["Anil Kumar J"], ["Mahantesh Patil"], "FIR-401/BGT/2026", "IPC 323, 324", "medium", 20),
    ("CR-2026-HVR-001", "Domestic Violence", "Haveri Town Police Station", -28, "open", "repeat domestic assault complaint", [], ["Kavita Banakar"], "FIR-501/HVR/2026", "DV Act", "medium", 15),
    ("CR-2026-KLB-001", "Property Disputes", "Chowk Police Station", -15, "closed", "survey intimidation, prior offender density", ["Karthik Gowda"], [], "FIR-122/KLB/2026", "IPC 447, 506", "low", 100),
    ("CR-2026-KLB-002", "Illegal Mining Violations", "Afzalpur Road Police Station", -8, "open", "illegal sand mining from riverbed", ["Javed Sheikh"], ["Ismail Nadaf"], "FIR-123/KLB/2026", "MMDR Act 21", "high", 30),
    ("CR-2026-YDG-001", "Theft & Burglaries", "Yadagir Town Police Station", -20, "investigating", "cash van robbery attempt", ["Vijay Kumar S"], [], "FIR-601/YDG/2026", "IPC 392, 397", "critical", 35),
    ("CR-2026-BDR-001", "Narcotics Smuggling Services", "Bidar Town Police Station", -12, "open", "synthetic drug manufacturing unit raided", ["Rahul Deshpande", "Zaheer Ahmed"], [], "FIR-701/BDR/2026", "NDPS 21, 22, 29", "critical", 20),
    ("CR-2026-BDR-002", "Assault", "Homnabad Police Station", -30, "closed", "communal tension assault incident", [], [], "FIR-702/BDR/2026", "IPC 323, 147", "high", 100),
    ("CR-2026-KPL-001", "Cyber Crime & Online Fraud", "Koppal Town Police Station", -9, "open", "UPI payment fraud via fake QR code", ["Naveen Reddy"], [], "FIR-801/KPL/2026", "IPC 420, IT Act 66D", "high", 10),

    # === CENTRAL KARNATAKA ===
    ("CR-2026-BNG-001", "Cyber Crime & Online Fraud", "Whitefield Police Station", -3, "open", "forged biometric login, micro-lending extortion", ["Vikram Yadav"], ["K. S. Narayanan"], "FIR-045/BNG/2026", "IPC 420, IT Act 66D", "high", 45),
    ("CR-2026-BNG-002", "Cyber Crime & Online Fraud", "KR Puram Police Station", -8, "open", "wallet mule routing, call spoofing", ["Vikram Yadav"], ["K. S. Narayanan"], "FIR-052/BNG/2026", "IPC 419, IT Act 66C", "medium", 25),
    ("CR-2026-BNG-003", "Theft & Burglaries", "Koramangala Police Station", -6, "open", "apartment burglary, smart lock bypass", ["Ramu Swamy"], ["Anupama Sharma"], "FIR-053/BNG/2026", "IPC 380, 457", "medium", 40),
    ("CR-2026-BNG-004", "Cyber Crime & Online Fraud", "HSR Layout Police Station", -14, "investigating", "cryptocurrency exchange scam", ["Farhan Ahmed"], ["Sunita Devi"], "FIR-054/BNG/2026", "IPC 420, IT Act 66D", "critical", 55),
    ("CR-2026-BNG-005", "Narcotics Smuggling Services", "Jayanagar Police Station", -11, "open", "MDMA distribution network, college area", ["Khalid Mehmood"], [], "FIR-055/BNG/2026", "NDPS 21, 22", "high", 20),
    ("CR-2026-BNG-006", "Assault", "Whitefield Police Station", -25, "closed", "gated community altercation, weapon recovered", ["Anil Kumar J"], ["Dinesh Rao"], "FIR-056/BNG/2026", "IPC 323, 324, 506", "medium", 100),
    ("CR-2026-BRL-001", "Theft & Burglaries", "Devanahalli Police Station", -17, "open", "farm equipment theft, GPS trackers removed", ["Vijay Kumar S"], ["Vijaya Kumari"], "FIR-601/BRL/2026", "IPC 379", "medium", 30),
    ("CR-2026-BRL-002", "Illegal Mining Violations", "Hoskote Police Station", -13, "open", "illegal granite quarry expansion", ["Satish Mudiraj", "Tariq Hussain"], [], "FIR-602/BRL/2026", "MMDR Act 21", "high", 25),
    ("CR-2026-TMK-001", "Assault", "Town Police Station", -31, "closed", "industrial road altercation", [], [], "FIR-144/TMK/2026", "IPC 323", "medium", 100),
    ("CR-2026-TMK-002", "Smuggling & Excise Violations", "Tiptur Police Station", -19, "open", "illicit liquor distillery raid", ["Lokesh Biradar"], [], "FIR-145/TMK/2026", "Excise Act 32", "medium", 35),
    ("CR-2026-KLR-001", "Theft & Burglaries", "Kolar Town Police Station", -22, "open", "gold jewellery heist during festival", ["Mohammed Ali"], ["Chandrakala Devi"], "FIR-901/KLR/2026", "IPC 379, 392", "high", 40),
    ("CR-2026-KLR-002", "Narcotics Smuggling Services", "Bangarapet Police Station", -7, "investigating", "cannabis supply chain from Andhra border", ["Imran Khan Pathan"], [], "FIR-902/KLR/2026", "NDPS 20, 21", "high", 15),
    ("CR-2026-CB-001", "Property Disputes", "Chikkaballapura Town Police Station", -26, "open", "temple land encroachment, forged records", ["Mahesh Jain"], [], "FIR-951/CB/2026", "IPC 447, 468", "low", 50),
    ("CR-2026-RMN-001", "Theft & Burglaries", "Ramanagara Town Police Station", -16, "investigating", "highway cargo truck hijacking", ["Ganesh Haldipur"], [], "FIR-961/RMN/2026", "IPC 392, 395", "critical", 30),
    ("CR-2026-RMN-002", "Assault", "Channapatna Police Station", -29, "closed", "political rally violence, multiple injuries", [], [], "FIR-962/RMN/2026", "IPC 323, 147, 148", "high", 100),
    ("CR-2026-HSN-001", "Domestic Violence", "City Police Station", -23, "open", "repeat household assault complaint", [], ["Hema Malini"], "FIR-208/HSN/2026", "DV Act", "medium", 30),
    ("CR-2026-HSN-002", "Cyber Crime & Online Fraud", "Arsikere Police Station", -10, "open", "fake customer care scam targeting farmers", ["Sunil Khot"], ["Ramesh Gowda"], "FIR-209/HSN/2026", "IPC 420, IT Act 66D", "medium", 20),
    ("CR-2026-HSN-003", "Theft & Burglaries", "City Police Station", -33, "closed", "temple hundi theft, CCTV footage recovered", ["Vijay Kumar S"], [], "FIR-210/HSN/2026", "IPC 380", "medium", 100),
    ("CR-2026-MND-001", "Domestic Violence", "Mandya Town Police Station", -14, "open", "dowry harassment and physical assault", [], ["Shashikala Devi"], "FIR-301/MND/2026", "DV Act, IPC 498A", "medium", 25),
    ("CR-2026-MND-002", "Smuggling & Excise Violations", "Srirangapatna Police Station", -21, "open", "illicit arrac transport via highway", ["Lokesh Biradar"], [], "FIR-302/MND/2026", "Excise Act 32", "medium", 30),
    ("CR-2026-CTD-001", "Illegal Mining Violations", "Chitradurga Town Police Station", -18, "investigating", "illegal iron ore extraction near highway", ["Mohsin Pasha", "Javed Sheikh"], ["Vasanth Kumar"], "FIR-401/CTD/2026", "MMDR Act 21", "high", 45),
    ("CR-2026-CTD-002", "Theft & Burglaries", "Hiriyur Police Station", -27, "open", "warehouse break-in, power tools stolen", ["Rohit Shetty K"], [], "FIR-402/CTD/2026", "IPC 379, 457", "medium", 15),

    # === SOUTH KARNATAKA ===
    ("CR-2026-MYS-001", "Theft & Burglaries", "Devaraja Police Station", -6, "open", "late night lock break, scooter reconnaissance", ["Ramu Swamy", "Karthik Gowda"], ["Dr. Vinay Murthy"], "FIR-789/MYS/2026", "IPC 379, 457", "high", 60),
    ("CR-2026-MYS-002", "Theft & Burglaries", "Devaraja Police Station", -18, "closed", "repeat balcony entry, jewellery targeting", ["Ramu Swamy"], ["Dr. Vinay Murthy"], "FIR-790/MYS/2026", "IPC 380", "medium", 100),
    ("CR-2026-MYS-003", "Cyber Crime & Online Fraud", "Nazarbad Police Station", -9, "open", "UPI fraud via fake merchant QR codes", ["Naveen Reddy"], ["Jyothi Lingegowda"], "FIR-791/MYS/2026", "IPC 420, IT Act 66D", "high", 30),
    ("CR-2026-MYS-004", "Narcotics Smuggling Services", "Vani Vilas Mohalla Police Station", -4, "open", "MDMA delivery via dark web, dead drop", ["Rahul Deshpande"], [], "FIR-792/MYS/2026", "NDPS 21, 22", "critical", 10),
    ("CR-2026-MYS-005", "Assault", "Devaraja Police Station", -32, "closed", "market dispute turned violent, knife recovered", ["Anil Kumar J"], ["Chitra K"], "FIR-793/MYS/2026", "IPC 324, 506", "medium", 100),
    ("CR-2026-CMR-001", "Assault", "Chamarajanagar Town Police Station", -16, "open", "village boundary dispute assault", ["Manoj Birajdar"], ["Manjula Devi"], "FIR-801/CMR/2026", "IPC 323, 324", "medium", 20),
    ("CR-2026-CMR-002", "Property Disputes", "Gundlupet Police Station", -24, "investigating", "encroachment of SC/ST land, forged title", ["Mahesh Jain"], [], "FIR-802/CMR/2026", "IPC 447, 468", "medium", 40),
    ("CR-2026-KDG-001", "Smuggling & Excise Violations", "Madikeri Town Police Station", -11, "open", "coffee estate timber smuggling, midnight transport", ["Bharath Gowda"], ["Kaveri Poojary"], "FIR-851/KDG/2026", "Excise Act, Forest Act", "high", 25),
    ("CR-2026-KDG-002", "Theft & Burglaries", "Virajpet Police Station", -20, "open", "resort burglary, tourist valuables stolen", ["Vijay Kumar S"], [], "FIR-852/KDG/2026", "IPC 379, 457", "medium", 35),
    ("CR-2026-DVG-001", "Theft & Burglaries", "Davanagere Town Police Station", -13, "open", "textile shop break-in, goods worth 12L stolen", ["Rohit Shetty K"], ["Padmavathi"], "FIR-501/DVG/2026", "IPC 379, 457", "high", 30),
    ("CR-2026-DVG-002", "Narcotics Smuggling Services", "Harpanahalli Police Station", -8, "investigating", "ganja supply chain from Goa route", ["Imran Khan Pathan", "Zaheer Ahmed"], [], "FIR-502/DVG/2026", "NDPS 20, 21", "critical", 15),
    ("CR-2026-SHG-001", "Smuggling & Excise Violations", "Shimoga Town Police Station", -17, "open", "illegal sand mining from Tunga riverbed", ["Tariq Hussain"], ["Arun Kumar"], "FIR-601/SHG/2026", "MMDR Act 21", "high", 20),
    ("CR-2026-SHG-002", "Cyber Crime & Online Fraud", "Sagara Police Station", -22, "open", "online ticket booking scam, festival rush", ["Sunil Khot"], [], "FIR-602/SHG/2026", "IPC 420, IT Act 66D", "medium", 15),
    ("CR-2026-CMG-001", "Theft & Burglaries", "Chikkamagaluru Town Police Station", -19, "open", "coffee estate equipment theft at night", ["Rohit Shetty K"], [], "FIR-701/CMG/2026", "IPC 379, 457", "medium", 25),
    ("CR-2026-CMG-002", "Assault", "Kadur Police Station", -28, "closed", "property dispute assault, hospitalisation", [], [], "FIR-702/CMG/2026", "IPC 323, 324", "medium", 100),
    ("CR-2026-BLR-001", "Illegal Mining Violations", "Rural Police Station", -13, "open", "night mineral transport convoy", ["Mohsin Pasha"], [], "FIR-611/BLR/2026", "MMDR Act 21", "high", 80),
    ("CR-2026-BLR-002", "Narcotics Smuggling Services", "City Police Station", -10, "open", "pharmaceutical drug diversion ring", ["Zaheer Ahmed"], [], "FIR-612/BLR/2026", "NDPS 21, 22", "high", 35),
    ("CR-2026-RCR-001", "Narcotics Smuggling Services", "Raichur Town Police Station", -15, "open", "cross-border cannabis smuggling via train", ["Imran Khan Pathan"], [], "FIR-801/RCR/2026", "NDPS 20, 21", "critical", 20),
    ("CR-2026-RCR-002", "Property Disputes", "Mantralayam Road Police Station", -25, "investigating", "temple land encroachment by builder", ["Rakesh Tiwari"], [], "FIR-802/RCR/2026", "IPC 447, 468, 506", "medium", 40),
    ("CR-2026-VJN-001", "Illegal Mining Violations", "Hospet Town Police Station", -9, "open", "illegal iron ore transport, weighbridge tampering", ["Mohsin Pasha", "Tariq Hussain"], [], "FIR-851/VJN/2026", "MMDR Act 21", "high", 25),
    ("CR-2026-VJN-002", "Theft & Burglaries", "Sandur Police Station", -21, "open", "mining equipment theft from depot", ["Vijay Kumar S"], [], "FIR-852/VJN/2026", "IPC 379", "medium", 30),

    # === COASTAL KARNATAKA ===
    ("CR-2026-MNG-001", "Narcotics Smuggling Services", "Pandeshwar Police Station", -4, "open", "synthetic MDMA harbor handoff", ["Sayed Ibrahim"], ["Asha Rao"], "FIR-331/MNG/2026", "NDPS 21, 22", "critical", 15),
    ("CR-2026-MNG-002", "Theft & Burglaries", "Pandeshwar Police Station", -12, "open", "gold chain snatching at traffic signal", ["Mohammed Ali"], ["Fathima Begum"], "FIR-332/MNG/2026", "IPC 392, 356", "high", 35),
    ("CR-2026-MNG-003", "Cyber Crime & Online Fraud", "Surathkal Police Station", -8, "open", "hawala money transfer via crypto", ["Farhan Ahmed"], ["Ayesha Parveen"], "FIR-333/MNG/2026", "IPC 420, IT Act 66D, PMLA", "critical", 20),
    ("CR-2026-MNG-004", "Assault", "Surathkal Police Station", -27, "closed", "road rage assault with weapon", [], ["Irfan Ahmed"], "FIR-334/MNG/2026", "IPC 324, 506", "medium", 100),
    ("CR-2026-MNG-005", "Smuggling & Excise Violations", "Puttur Police Station", -14, "open", "illicit cashew nut export, forged manifests", ["Ganesh Haldipur"], [], "FIR-335/MNG/2026", "Excise Act 32", "medium", 25),
    ("CR-2026-UDP-001", "Theft & Burglaries", "Udupi Town Police Station", -16, "investigating", "temple treasury theft, inner sanctum access", ["Rajesh Pai"], ["Sunanda Poojary"], "FIR-401/UDP/2026", "IPC 380, 457", "high", 40),
    ("CR-2026-UDP-002", "Cyber Crime & Online Fraud", "Kapu Police Station", -11, "open", "fake fishing license portal scam", ["Sunil Khot"], [], "FIR-402/UDP/2026", "IPC 420, IT Act 66D", "medium", 15),
    ("CR-2026-UKN-001", "Smuggling & Excise Violations", "Karwar Town Police Station", -13, "open", "coastal smuggling of electronics via fishing boats", ["Irfan Hassan", "Nasir Shaikh"], ["Rajesh Kharvi"], "FIR-501/UKN/2026", "Excise Act, Customs Act", "high", 30),
    ("CR-2026-UKN-002", "Narcotics Smuggling Services", "Sirsi Police Station", -20, "open", "ganja cultivation in forest fringe area", ["Imran Khan Pathan"], [], "FIR-502/UKN/2026", "NDPS 20, 21", "critical", 15),
    ("CR-2026-UKN-003", "Assault", "Yellapur Police Station", -34, "closed", "tribal land dispute violence", [], [], "FIR-503/UKN/2026", "IPC 323, 147", "medium", 100),
]

# District -> Officer badge mapping for realistic case assignment
DISTRICT_OFFICER_MAP = {
    "Belagavi": ["IO-1247", "SI-3382"],
    "Dharwad": ["IO-5501"],
    "Gadag": ["SI-2290"],
    "Haveri": ["SI-8812"],
    "Bagalkote": ["IO-7734"],
    "Vijayapura": ["IO-6623"],
    "Kalaburagi": ["SI-4419"],
    "Yadagir": ["SI-1156"],
    "Bidar": ["IO-9945"],
    "Koppal": [],
    "Bengaluru Urban": ["IO-2267", "SI-3378", "IO-4489"],
    "Bengaluru Rural": ["SI-5590"],
    "Tumkuru": ["IO-6601"],
    "Kolar": ["SI-7712"],
    "Chikkaballapura": [],
    "Ramanagara": ["SI-2156"],
    "Hassan": ["IO-8823"],
    "Mandya": ["SI-9934"],
    "Chitradurga": ["IO-1045"],
    "Mysuru": ["IO-3921", "IO-3267"],
    "Chamarajanagar": ["SI-4378"],
    "Kodagu": ["IO-5489"],
    "Shimoga": ["SI-6590"],
    "Davanagere": ["IO-7601"],
    "Chikkamagaluru": ["SI-8712"],
    "Ballari": [],
    "Raichur": [],
    "Vijayanagara": [],
    "Dakshina Kannada": ["IO-9823", "SI-0934"],
    "Udupi": ["IO-1046"],
    "Uttara Kannada": ["SI-2157"],
}


def _generate_synthetic_cases():
    """Generate 25 additional synthetic cases spread across all districts."""
    rng = random.Random(42)
    category_names = [c[0] for c in CATEGORIES]
    station_map = {loc[2]: loc[1] for loc in LOCATIONS}
    stations = list(station_map.keys())

    criminal_names = [c[0] for c in CRIMINALS]
    victim_names = [v[0] for v in VICTIMS]

    statuses = ["open", "open", "open", "closed", "investigating"]
    priorities = ["low", "medium", "medium", "high", "critical"]

    cases = []

    for i in range(25):
        cat = rng.choice(category_names)
        station = rng.choice(stations)
        days_ago = rng.randint(1, 365)
        status = rng.choice(statuses)
        priority = rng.choice(priorities)
        progress = rng.randint(0, 100) if status == "closed" else rng.randint(5, 80)
        n_criminals = rng.choices([0, 1, 2, 3], weights=[30, 40, 20, 10])[0]
        n_victims = rng.choices([0, 1, 2], weights=[40, 45, 15])[0]
        selected_criminals = rng.sample(
            [c for c in criminal_names if c not in ["Ramu Swamy", "Vikram Yadav", "Sayed Ibrahim", "Karthik Gowda", "Mohsin Pasha"]],
            min(n_criminals, 55),
        )
        selected_victims = rng.sample(victim_names, min(n_victims, len(victim_names)))

        case_num = f"CR-2026-SYN-{i+1:03d}"
        fir_num = f"FIR-{rng.randint(200,999)}/SYN/2026"
        mo_options = [
            "night operation, mask used", "vehicle reconnaissance, parked getaway bike",
            "insider tip suspected", "repeated pattern across districts", "fake identity documents",
            "coordinated group activity", "electronic surveillance evasion", "cash-only transactions",
            "modified vehicle plates", "warehouse hideout used",
        ]
        mo_tags = ", ".join(rng.sample(mo_options, rng.randint(1, 3)))
        sections = rng.choice([
            "IPC 379, 457", "IPC 420, IT Act 66D", "NDPS 21", "IPC 323, 324",
            "MMDR Act 21", "DV Act", "IPC 447, 506", "Excise Act 32",
        ])

        cases.append((case_num, cat, station, -days_ago, status, mo_tags, selected_criminals, selected_victims, fir_num, sections, priority, progress))
    return cases


ALL_CASES = CASES + _generate_synthetic_cases()


DEMO_NOTIFICATIONS = [
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
    ("IO-9823", "SCRB-7740", "Harbor Surveillance Anomaly — Mangaluru", "intelligence_sharing", "intelligence_sharing", "Unusual Vessel Activity Detected", "Coastal surveillance cameras flagged unregistered vessel near Old Port at 02:15. Cross-reference with CR-2026-MNG-001 suspect network. Requesting satellite tracking support.", "high", "high", "unread", "CR-2026-MNG-001", "FIR-331/MNG/2026", False, 1),
    ("IO-2267", "SP-0088", "Cyber Crime Surge — Koramangala Division", "case_escalation", "case_escalation", "Escalation: 4 Cyber Cases in 10 Days", "Four cybercrime reports in Koramangala within 10 days suggest organized cell. UPI fraud, phishing, crypto scam patterns overlap. Requesting SCRB analysis and inter-district coordination.", "critical", "critical", "unread", "CR-2026-BNG-003", "FIR-053/BNG/2026", False, 3),
    ("IO-9945", "IO-3921", "Cross-District Narcotics Link — Bidar-Hyderabad", "intelligence_sharing", "intelligence_sharing", "Interstate Drug Route Identified", "Investigation reveals drug supply chain from Bidar to Hyderabad via Tandur. Suspects linked to CR-2026-BDR-001. Requesting AP-TS border coordination.", "critical", "critical", "unread", "CR-2026-BDR-001", "FIR-701/BDR/2026", False, 6),
]


def seed() -> None:
    from app.database.postgres import Base, engine
    Base.metadata.create_all(bind=engine)
    try:
        from app.main import _migrate_user_lockout_columns, _migrate_notifications_table, _migrate_criminals_table, _migrate_provenance_columns
        _migrate_user_lockout_columns()
        _migrate_notifications_table()
        _migrate_criminals_table()
        _migrate_provenance_columns()
    except Exception:
        pass
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

        # Issue #144 gap 132.1: backfill the normalized MO tag relations from
        # the seeded mo_tags/mo_summary fields so pattern detection works out
        # of the box. Idempotent — safe on already-seeded databases.
        try:
            from app.services.mo_pattern_service import sync_mo_tags

            stats = sync_mo_tags(db)
            print(
                "MO sync: "
                f"{stats['case_links_created']} case links + "
                f"{stats['criminal_links_created']} criminal links "
                f"({stats['tags_created']} new tags)"
            )
        except Exception as exc:  # never fail seeding over analytics backfill
            print(f"MO sync skipped: {exc}")

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

    # 1) Seed demo-user officers (IO-3921, SP-0088 — linked to User accounts)
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
                dataset_provenance=_SEED_PROVENANCE,
            )
            db.add(officer)
            db.flush()
        elif getattr(officer, "dataset_provenance", None) in (None, "live", "unknown", ""):
            officer.dataset_provenance = _SEED_PROVENANCE
            db.flush()
        officers[badge] = officer

    # 2) Seed standalone officers (no user login — appear in officer directory)
    for payload in STANDALONE_OFFICERS:
        badge = payload["badge_number"]
        officer = db.query(Officer).filter(Officer.badge_number == badge).first()
        if not officer:
            officer = Officer(
                user_id=None,
                badge_number=badge,
                name=payload["name"],
                rank=payload["rank"],
                district=payload["district"],
                station=payload["station"],
                designation=payload.get("designation"),
                phone=payload.get("phone"),
                email=payload.get("email"),
                status="active",
                dataset_provenance=_SEED_PROVENANCE,
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
            location = Location(address=address, district=district, station=station, latitude=lat, longitude=lng, pincode=pincode, dataset_provenance=_SEED_PROVENANCE)
            db.add(location)
            db.flush()
        elif getattr(location, "dataset_provenance", None) in (None, "live", "unknown", ""):
            location.dataset_provenance = _SEED_PROVENANCE
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
                dataset_provenance=_SEED_PROVENANCE,
            )
            db.add(criminal)
            db.flush()
        elif getattr(criminal, "dataset_provenance", None) in (None, "live", "unknown", ""):
            criminal.dataset_provenance = _SEED_PROVENANCE
            db.flush()
        criminals[full_name] = criminal
    return criminals


def _seed_victims(db):
    victims = {}
    for full_name, contact, address, gender, age, statement in VICTIMS:
        victim = db.query(Victim).filter(Victim.full_name == full_name, Victim.contact_number == contact).first()
        if not victim:
            victim = Victim(full_name=full_name, contact_number=contact, address=address, gender=gender, age=age, statement=statement, dataset_provenance=_SEED_PROVENANCE)
            db.add(victim)
            db.flush()
        elif getattr(victim, "dataset_provenance", None) in (None, "live", "unknown", ""):
            victim.dataset_provenance = _SEED_PROVENANCE
            db.flush()
        victims[full_name] = victim
    return victims


def _seed_cases_and_firs(db, categories, locations, criminals, victims, officers):
    now = datetime.now()

    # Build district -> station mapping for officer lookup
    station_district = {loc[2]: loc[1] for loc in LOCATIONS}

    # Build a mapping of officer badge -> officer object for standalone officers
    standalone_officers_by_badge = {}
    for payload in STANDALONE_OFFICERS:
        badge = payload["badge_number"]
        if badge in officers:
            standalone_officers_by_badge[badge] = officers[badge]

    for item in ALL_CASES:
        case_number, category_name, station, days, status, mo_tags, criminal_names, victim_names, fir_number, sections, priority, progress = item
        crime = db.query(CrimeCase).filter(CrimeCase.case_number == case_number).first()

        # Determine the best officer for this case based on district
        district = station_district.get(station, "State HQ")
        district_badges = DISTRICT_OFFICER_MAP.get(district, [])
        assigned_officer = None
        for badge in district_badges:
            if badge in officers:
                assigned_officer = officers[badge]
                break
        if not assigned_officer:
            # Fallback: pick any officer from the same district
            for badge, off in standalone_officers_by_badge.items():
                if off.district == district:
                    assigned_officer = off
                    break
        if not assigned_officer:
            # Final fallback: use IO-3921
            assigned_officer = officers.get("IO-3921") or next(iter(officers.values()), None)

        # Compute realistic, distinct occurrence time for each case based on case_number and category
        h_hash = abs(hash(case_number))
        if "Theft" in category_name or "Burglar" in category_name:
            hour = (21 + (h_hash % 7)) % 24  # 21:00 to 03:00 (night burglaries)
        elif "Cyber" in category_name or "Online" in category_name:
            hour = 10 + (h_hash % 9)  # 10:00 to 18:00 (business hours)
        elif "Narcotics" in category_name or "Smuggling" in category_name:
            hour = (20 + (h_hash % 8)) % 24  # 20:00 to 03:00
        elif "Mining" in category_name:
            hour = (23 + (h_hash % 6)) % 24  # 23:00 to 04:00 (night transport)
        elif "Domestic" in category_name:
            hour = 18 + (h_hash % 5)  # 18:00 to 22:00
        else:
            hour = 8 + (h_hash % 14)  # 08:00 to 21:00

        minute = (h_hash % 12) * 5
        case_date = (now + timedelta(days=days)).date()
        case_occurred_at = datetime.combine(case_date, time(hour, minute, 0))
        case_reported_at = case_occurred_at + timedelta(hours=1 + (h_hash % 4), minutes=((h_hash // 7) % 12) * 5)

        if not crime:
            crime = CrimeCase(
                case_number=case_number,
                category_id=categories[category_name].id,
                location_id=locations[station].id,
                occurred_at=case_occurred_at,
                reported_at=case_reported_at,
                description=f"{category_name} reported at {locations[station].address}, {district}",
                mo_tags=mo_tags,
                status=status,
                priority=priority,
                progress=progress,
                assigned_officer_id=assigned_officer.id if assigned_officer else None,
                dataset_provenance=_SEED_PROVENANCE,
            )
            db.add(crime)
            db.flush()
        else:
            crime.occurred_at = case_occurred_at
            crime.reported_at = case_reported_at
            crime.priority = priority
            crime.progress = progress
            if getattr(crime, "dataset_provenance", None) in (None, "live", "unknown", ""):
                crime.dataset_provenance = _SEED_PROVENANCE
            if not crime.assigned_officer_id and assigned_officer:
                crime.assigned_officer_id = assigned_officer.id
            db.flush()

        fir = db.query(FIR).filter(FIR.fir_number == fir_number).first()
        if not fir:
            import json
            fir = FIR(
                fir_number=fir_number,
                crime_case_id=crime.id,
                investigating_officer_id=assigned_officer.id if assigned_officer else None,
                complainant_name=victim_names[0] if victim_names else "State Complainant",
                complainant_contact=victims[victim_names[0]].contact_number if victim_names and victim_names[0] in victims else None,
                sections=sections,
                status="registered" if status == "open" else "closed",
                filed_at=case_reported_at + timedelta(minutes=15),
                narrative=f"Backend-seeded FIR for {case_number}; derived from the Police FIR ER model.",
                attachments=json.dumps([
                    {"name": f"complaint_copy_{case_number}.pdf", "size": 154200},
                    {"name": f"spot_mahazar_{case_number}.pdf", "size": 284100},
                ]),
                dataset_provenance=_SEED_PROVENANCE,
            )
            db.add(fir)
            db.flush()
        else:
            fir.filed_at = case_reported_at + timedelta(minutes=15)
            if getattr(fir, "dataset_provenance", None) in (None, "live", "unknown", ""):
                fir.dataset_provenance = _SEED_PROVENANCE
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
            if "Cyber" in category_name:
                ev_type = "digital"
                ev_title = f"Digital Forensics — {case_number}"
                ev_desc = f"Digital evidence including device images, network logs, and transaction records for {case_number}."
            elif "Narcotics" in category_name or "Smuggling" in category_name:
                ev_type = "physical"
                ev_title = f"Narcotics Seizure Kit — {case_number}"
                ev_desc = f"Physical evidence including seized substances, packaging materials, and transport vehicle documentation for {case_number}."
            elif "Theft" in category_name or "Burglar" in category_name:
                ev_type = "physical"
                ev_title = f"Burglary Evidence Packet — {case_number}"
                ev_desc = f"Physical evidence including tool marks, fingerprints, and stolen property inventory for {case_number}."
            elif "Assault" in category_name:
                ev_type = "document"
                ev_title = f"Assault Case Documentation — {case_number}"
                ev_desc = f"Medical reports, witness statements, and scene photographs for assault case {case_number}."
            elif "Mining" in category_name:
                ev_type = "document"
                ev_title = f"Mining Violation Records — {case_number}"
                ev_desc = f"Satellite imagery, transit manifests, and forged permits for illegal mining case {case_number}."
            elif "Domestic" in category_name:
                ev_type = "document"
                ev_title = f"DV Case Evidence — {case_number}"
                ev_desc = f"Medical examination reports, complaint statements, and photographic evidence for {case_number}."
            else:
                ev_type = "document"
                ev_title = f"Case Evidence — {case_number}"
                ev_desc = f"Supporting documentation and evidence for {case_number}."

            ev_status = "Analyzed" if status == "closed" else "Under Analysis" if progress > 30 else "Pending"
            badge = assigned_officer.badge_number if assigned_officer else "SCRB"
            officer_name = assigned_officer.name if assigned_officer else "SCRB Analyst"

            evidence = Evidence(
                case_id=crime.id,
                title=ev_title,
                evidence_type=ev_type,
                description=ev_desc,
                created_by=officer_name,
                status=ev_status,
                storage_path=f"/evidence/{crime.id}/{ev_type}_packet",
                dataset_provenance=_SEED_PROVENANCE,
            )
            db.add(evidence)
            db.flush()

            db.add(ChainOfCustody(
                evidence_id=evidence.id,
                from_user=assigned_officer.user_id if assigned_officer else None,
                to_user=assigned_officer.user_id if assigned_officer else None,
                action="Evidence Registered",
                location=locations[station].address if station in locations else "Unknown",
                remarks=f"Evidence logged for case {case_number}",
            ))

            if progress > 30:
                db.add(ChainOfCustody(
                    evidence_id=evidence.id,
                    from_user=assigned_officer.user_id if assigned_officer else None,
                    to_user=assigned_officer.user_id if assigned_officer else None,
                    action="Forensic Analysis Initiated",
                    location="Forensic Lab",
                    remarks="Evidence submitted for forensic examination",
                ))

            if status == "closed":
                db.add(ChainOfCustody(
                    evidence_id=evidence.id,
                    from_user=assigned_officer.user_id if assigned_officer else None,
                    to_user=assigned_officer.user_id if assigned_officer else None,
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

    # Seed demo interventions for strategic prevention loop
    if db.query(Intervention).count() == 0:
        admin_user = user_objs.get("admin")
        interventions_data = [
            {
                "district": "Bengaluru Urban",
                "intervention_type": "patrol_surge",
                "title": "Operation Garuda: Koramangala & Indiranagar Night Patrol Surge",
                "description": "High-visibility saturation patrols and mobile interceptors to curtail late-night thefts and street offenses.",
                "started_at": datetime.now() - timedelta(days=60),
                "ended_at": datetime.now() - timedelta(days=5),
                "status": "completed",
            },
            {
                "district": "Mysuru",
                "intervention_type": "checkpoint_blitz",
                "title": "Expressway Checkpoint Blitz & Inter-City Transit Screening",
                "description": "Static and dynamic multi-point checkpoints deployed at key transit arteries to disrupt organized contraband transit.",
                "started_at": datetime.now() - timedelta(days=45),
                "ended_at": None,
                "status": "active",
            },
            {
                "district": "Dakshina Kannada",
                "intervention_type": "cctv_deployment",
                "title": "Coastal & Port Sector Smart CCTV Surveillance Rollout",
                "description": "Deployment of high-definition ANPR-enabled surveillance feeds covering critical logistics corridors.",
                "started_at": datetime.now() - timedelta(days=90),
                "ended_at": datetime.now() - timedelta(days=10),
                "status": "completed",
            },
            {
                "district": "Dharwad",
                "intervention_type": "special_drive",
                "title": "Hubballi-Dharwad Women & Student Safety Escort Drive",
                "description": "Intensive beat patrolling around educational hubs and commercial zones during peak commute windows.",
                "started_at": datetime.now() - timedelta(days=30),
                "ended_at": None,
                "status": "active",
            },
            {
                "district": "Belagavi",
                "intervention_type": "lighting_upgrade",
                "title": "Industrial Corridor High-Mast Illumination & Beat Expansion",
                "description": "Infrastructure lighting intervention paired with enhanced evening beat coverage to deter property offenses.",
                "started_at": datetime.now() - timedelta(days=75),
                "ended_at": datetime.now() - timedelta(days=15),
                "status": "completed",
            },
        ]
        for item in interventions_data:
            inv = Intervention(
                **item,
                created_by_id=admin_user.id if admin_user else None,
            )
            db.add(inv)
        db.flush()
        print(f"Seeded {len(interventions_data)} demo interventions")


if __name__ == "__main__":
    seed()

