# TODO: Remove bcrypt, replace with simple SHA-256 password hashing

- [x] Step 1: Modify `backend/app/core/security.py` — Replace bcrypt `CryptContext` with `hashlib.sha256`
- [x] Step 2: Modify `backend/requirements.txt` — Remove `bcrypt`, `passlib`, and `passlib[bcrypt]` dependencies
- [x] Step 3: Re-seed database with new hashes (run: `python -m app.database.seed_db` from backend/)
- [ ] Done

