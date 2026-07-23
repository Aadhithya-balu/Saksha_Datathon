import urllib.request
import urllib.parse
import urllib.error
import json
import uuid

API_URL = "http://127.0.0.1:8000/api/v1"
TEST_USERS = [
    {"role": "Admin", "username": "admin", "password": "password"},
    {"role": "Investigator", "username": "IO-3921", "password": "123456"},
    {"role": "Inspector", "username": "INSP-1111", "password": "123456"},
    {"role": "Forensic", "username": "FOR-2222", "password": "123456"},
    {"role": "Crime Analyst", "username": "SCRB-7740", "password": "123456"}
]

def run_rbac_tests():
    fake_uuid = str(uuid.uuid4())
    endpoints = {
        "View Officers": {"method": "GET", "url": "/officers"},
        "Create Officer": {"method": "POST", "url": "/officers", "json": {}},
        "Create Evidence": {"method": "POST", "url": "/evidence", "json": {}},
        "Delete Evidence": {"method": "DELETE", "url": f"/evidence/{fake_uuid}"},
        "Assign Evidence": {"method": "POST", "url": f"/evidence/{fake_uuid}/assign", "json": {}},
        "Accept Assignment": {"method": "POST", "url": f"/evidence/{fake_uuid}/assignments/{fake_uuid}/accept"},
        "Upload Evidence": {"method": "POST", "url": f"/evidence/{fake_uuid}/upload"},
        "AI Summary": {"method": "POST", "url": f"/evidence/{fake_uuid}/summary"}
    }

    results = {}

    for user in TEST_USERS:
        role = user['role']
        print(f"\nTesting Role: {role}")
        results[role] = {}
        
        # Login
        data = json.dumps({"username": user['username'], "password": "123456"}).encode()
        req = urllib.request.Request(f"{API_URL}/auth/login", data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                token = json.loads(resp.read().decode()).get('access_token')
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"  Login Failed! {e}")
            continue
            
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        for name, ep in endpoints.items():
            url = API_URL + ep['url']
            method = ep['method']
            
            req = urllib.request.Request(url, method=method, headers=headers)
            if method == "POST" and "json" in ep:
                req.data = json.dumps(ep['json']).encode()
                
            if "upload" in url:
                boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
                headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
                body = (
                    f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
                    f'Content-Type: text/plain\r\n\r\n'
                    f'hello\r\n'
                    f'--{boundary}--\r\n'
                ).encode('utf-8')
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                
            try:
                with urllib.request.urlopen(req) as resp:
                    status = resp.status
            except urllib.error.HTTPError as e:
                status = e.code
            except urllib.error.URLError as e:
                print(f"  Connection error for {name}: {e}")
                continue
                
            allowed = status not in [401, 403]
            results[role][name] = "PASS" if allowed else "BLOCKED"
            print(f"  {name}: {status} -> {results[role][name]}")

if __name__ == "__main__":
    run_rbac_tests()
