import asyncio
import httpx
import os
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

async def create_dummy_image():
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save('test_evidence.jpg')
    return 'test_evidence.jpg'

async def main():
    image_path = await create_dummy_image()
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        response = await client.post("/auth/login", json={"username": "admin", "password": "password123"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = await client.get("/auth/me", headers=headers)
        user_id = me.json()["id"]

        print("--- EVIDENCE CRUD ---")
        # 1. Create crime case first, as evidence requires case_id
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('SUPABASE_DB_HOST'),
            port=os.getenv('SUPABASE_DB_PORT'),
            dbname=os.getenv('SUPABASE_DB_NAME'),
            user=os.getenv('SUPABASE_DB_USER'),
            password=os.getenv('SUPABASE_DB_PASSWORD'),
            sslmode=os.getenv('SUPABASE_DB_SSLMODE', 'require')
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM crime_cases LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO crime_cases (id, fir_number, title, status) VALUES (gen_random_uuid(), 'TEST-123', 'Test', 'Open') RETURNING id;")
            case_id = cursor.fetchone()[0]
            conn.commit()
        else:
            case_id = row[0]
        cursor.close()
        conn.close()
            
        # Create Evidence
        evidence_payload = {
            "case_id": case_id,
            "title": "Test Digital Evidence",
            "description": "A test image uploaded for metadata extraction",
            "evidence_type": "image"
        }
        res = await client.post("/evidence", json=evidence_payload, headers=headers)
        print("Create Evidence:", res.status_code)
        evidence_id = res.json()["id"]
        
        print("\n--- FILE UPLOAD ---")
        with open(image_path, "rb") as f:
            files = {"file": ("test_evidence.jpg", f, "image/jpeg")}
            up_res = await client.post(f"/evidence/{evidence_id}/upload", files=files, headers=headers)
            print("Upload:", up_res.status_code, up_res.text[:100])
            
        print("\n--- ASSIGNMENT WORKFLOW ---")
        assign_res = await client.post(f"/evidence/{evidence_id}/assign?assigned_to={user_id}", headers=headers)
        print("Assign:", assign_res.status_code)
        assignment_id = assign_res.json()["id"]
        
        accept_res = await client.post(f"/evidence/{evidence_id}/assignments/{assignment_id}/accept", headers=headers)
        print("Accept:", accept_res.status_code)
        
        complete_res = await client.post(f"/evidence/{evidence_id}/assignments/{assignment_id}/complete", headers=headers)
        print("Complete:", complete_res.status_code)
        
        # Test AI Summary
        print("\n--- AI SUMMARY ---")
        ai_res = await client.post(f"/evidence/{evidence_id}/summary", headers=headers)
        print("AI Summary:", ai_res.status_code, ai_res.text[:100])

if __name__ == "__main__":
    asyncio.run(main())
