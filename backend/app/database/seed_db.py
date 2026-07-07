"""
Seeds the canonical roles required by RBAC, plus demo operator accounts,
so the API is usable immediately after init_db.py.
Run: python -m app.database.seed_db
"""
from app.core.security import hash_password
from app.database.postgres import SessionLocal
from app.models.role import Role
from app.models.user import User

ROLES = ["admin", "crime_analyst", "investigator", "policymaker"]

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@saksha.local",
        "full_name": "Platform Administrator",
        "password": "ChangeMe123!",
        "role_name": "admin",
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
        "password": "123456",
        "role_name": "investigator",
        "district": "Mysuru",
        "station": "City Central",
    },
    {
        "username": "SP-0088",
        "email": "sp-0088@saksha.local",
        "full_name": "SP Anil Kumble",
        "password": "123456",
        "role_name": "policymaker",
        "district": "State HQ",
        "station": "KSP HQ",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        role_objs = {}
        for name in ROLES:
            role = db.query(Role).filter(Role.name == name).first()
            if not role:
                role = Role(name=name, description=f"{name} role")
                db.add(role)
                db.flush()
            role_objs[name] = role

        for payload in DEMO_USERS:
            if db.query(User).filter(User.username == payload["username"]).first():
                continue

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

        db.commit()
        print("Seed complete. Demo logins:")
        print("- admin / ChangeMe123!")
        print("- SCRB-7740 / 123456")
        print("- IO-3921 / 123456")
        print("- SP-0088 / 123456")
        print("CHANGE THESE PASSWORDS IMMEDIATELY IN ANY REAL DEPLOYMENT.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
