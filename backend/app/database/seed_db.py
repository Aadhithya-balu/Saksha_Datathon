"""Seed roles, operators, and an ER-shaped prototype crime dataset."""
from datetime import date, datetime, timedelta

from app.core.security import hash_password
from app.database.postgres import SessionLocal
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim

ROLES = ["admin", "crime_analyst", "investigator", "policymaker"]

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@saksha.local",
        "full_name": "Platform Administrator",
        "password": "ChangeMe123!",
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
]

VICTIMS = [
    ("K. S. Narayanan", "+91 98800 00001", "Bengaluru Urban", "Male", 52, "Reported biometric face ID bypass and loan extortion."),
    ("Dr. Vinay Murthy", "+91 98800 00002", "Mysuru", "Male", 46, "Reported night burglary and missing jewellery."),
    ("Asha Rao", "+91 98800 00003", "Mangaluru", "Female", 33, "Witnessed cargo handoff near harbor gate."),
    ("Prakash Jain", "+91 98800 00004", "Belagavi", "Male", 41, "Reported forged excise transport documents."),
    ("Latha Hegde", "+91 98800 00005", "Hassan", "Female", 29, "Filed domestic violence complaint with medical evidence."),
]

CASES = [
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
        db.commit()
        print("Seed complete. Prototype logins:")
        print("- admin / ChangeMe123!")
        print("- SCRB-7740 / 123456")
        print("- IO-3921 / 123456")
        print("- SP-0088 / 123456")
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
    for item in CASES:
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

        evidence_exists = db.query(Evidence).filter(Evidence.crime_case_id == crime.id).first()
        if not evidence_exists:
            db.add(
                Evidence(
                    crime_case_id=crime.id,
                    evidence_type="digital" if "Cyber" in category_name else "document",
                    description=f"Primary evidence packet for {case_number}",
                    collected_by=investigator.badge_number if investigator else "SCRB",
                    chain_of_custody="Collected, sealed, and logged in Saksha prototype registry.",
                )
            )


if __name__ == "__main__":
    seed()

