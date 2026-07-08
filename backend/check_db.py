import sys
sys.path.insert(0, '.')

from app.database.postgres import SessionLocal
from app.services.auth_service import authenticate_user, issue_tokens, _get_pin
from app.models.officer import Officer

db = SessionLocal()

# Get 5 real employees to show their KGID and derived PIN
print("=== Real Employee Login Credentials ===")
print(f"{'KGID':<15} {'PIN':<10} {'Name':<25} {'Rank':<35} {'Role'}")
print("-" * 100)

employees = db.query(Officer).limit(10).all()
for emp in employees:
    pin = _get_pin(emp.KGID)
    rank = emp.rank.RankName if emp.rank else "Unknown"
    from app.services.auth_service import RANK_ROLE_MAP
    role = RANK_ROLE_MAP.get(emp.RankID, "investigator")
    print(f"{emp.KGID:<15} {pin:<10} {emp.FirstName:<25} {rank:<35} {role}")

print("\n=== Testing Login for first 3 employees ===")
for emp in employees[:3]:
    pin = _get_pin(emp.KGID)
    try:
        session = authenticate_user(db, emp.KGID, pin)
        tokens = issue_tokens(session)
        print(f"LOGIN OK: {session.username} | role={session.role_name} | name={session.full_name}")
        print(f"  district={session.district} | station={session.station}")
        print(f"  token={tokens['access_token'][:50]}...")
    except Exception as e:
        print(f"LOGIN FAIL: {emp.KGID} — {e}")

db.close()
