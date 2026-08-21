import asyncio
import os
import httpx
from dotenv import load_dotenv
from passlib.context import CryptContext
import psycopg2

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user():
    # Insert test user directly into supabase using psycopg2
    conn = psycopg2.connect(
        host=os.getenv('SUPABASE_DB_HOST'),
        port=os.getenv('SUPABASE_DB_PORT'),
        dbname=os.getenv('SUPABASE_DB_NAME'),
        user=os.getenv('SUPABASE_DB_USER'),
        password=os.getenv('SUPABASE_DB_PASSWORD'),
        sslmode=os.getenv('SUPABASE_DB_SSLMODE', 'require')
    )
    cursor = conn.cursor()
    hashed_password = pwd_context.hash("password123")
    cursor.execute("""
        INSERT INTO users (id, username, email, full_name, hashed_password, role)
        VALUES (gen_random_uuid(), 'test_officer_99', 'test99@police.gov.in', 'Test Officer', %s, 'investigator')
        ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password;
    """, (hashed_password,))
    conn.commit()
    cursor.close()
    conn.close()
    print("User created!")


async def main():
    pass
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v2") as client:
        print("Logging in...")
        response = await client.post("/auth/login", json={"username": "admin", "password": "password123"})
        
        print("Login response:", response.status_code, response.text)
        if response.status_code != 200:
            print("Failed to login")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test getting current user
        me = await client.get("/auth/me", headers=headers)
        print("User:", me.json())

        # Test listing officers
        print("\n--- OFFICERS ---")
        officers = await client.get("/officers", headers=headers)
        print("List Officers:", officers.status_code, officers.text[:100])
        
        # Test creating officer
        print("Create Officer:")
        officer_data = {
            "name": "Test Officer API",
            "badge_number": "TEST-1234",
            "rank": "Inspector",
            "district": "Central",
            "station": "HQ",
            "user_id": me.json()["id"]
        }
        res = await client.post("/officers", json=officer_data, headers=headers)
        print("Create:", res.status_code, res.text)
        
        if res.status_code == 200 or res.status_code == 201:
            officer_id = res.json()["id"]
            
            print("Get Officer:")
            get_res = await client.get(f"/officers/{officer_id}", headers=headers)
            print(get_res.status_code, get_res.text[:100])
            
            print("Delete Officer:")
            del_res = await client.delete(f"/officers/{officer_id}", headers=headers)
            print(del_res.status_code, del_res.text)

        # Test listing evidence
        print("\n--- EVIDENCE ---")
        evidence = await client.get("/evidence", headers=headers)
        print("List Evidence:", evidence.status_code, evidence.text[:100])
        

if __name__ == "__main__":
    asyncio.run(main())
