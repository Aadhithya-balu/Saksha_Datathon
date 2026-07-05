"""
Seeds the four canonical roles required by RBAC, plus one admin user,
so the API is usable immediately after init_db.py.
Run: python -m app.database.seed_db
"""
from app.core.security import hash_password
from app.database.postgres import SessionLocal
from app.models.role import Role
from app.models.user import User

ROLES = ["admin", "crime_analyst", "investigator", "policymaker"]


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

        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                email="admin@saksha.local",
                full_name="Platform Administrator",
                hashed_password=hash_password("ChangeMe123!"),
                role_id=role_objs["admin"].id,
                is_active=True,
            )
            db.add(admin)

        db.commit()
        print("Seed complete. Default admin login -> username: admin / password: ChangeMe123!")
        print("CHANGE THIS PASSWORD IMMEDIATELY IN ANY REAL DEPLOYMENT.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
