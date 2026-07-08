import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database.postgres import SessionLocal
from app.models.officer import Officer

db = SessionLocal()
try:
    emp = db.query(Officer).filter(Officer.KGID == 'KG996382').first()
    sys.stderr.write(f"Exact match: {emp.KGID if emp else 'NOT FOUND'}\n")

    like = db.query(Officer).filter(Officer.KGID.ilike('%996382%')).first()
    sys.stderr.write(f"Similar match: {like.KGID + ' ' + like.FirstName if like else 'NONE'}\n")

    total = db.query(Officer).count()
    sys.stderr.write(f"Total employees in table: {total}\n")

    # Show a few sample KGIDs
    samples = db.query(Officer.KGID).limit(5).all()
    sys.stderr.write(f"Sample KGIDs: {[r[0] for r in samples]}\n")
except Exception as e:
    sys.stderr.write(f"ERROR: {e}\n")
finally:
    db.close()
