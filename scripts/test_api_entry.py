import requests

# Test backend login & session
s = requests.Session()
login_res = s.post("http://localhost:5000/api/auth/login", json={"email": "a@a", "password": "a"})
print("Login status:", login_res.status_code, login_res.json())

# Fetch CSRF token
csrf_res = s.get("http://localhost:5000/api/auth/csrf-token")
csrf_token = csrf_res.json().get("csrf_token") if csrf_res.status_code == 200 else None
print("CSRF Token:", csrf_token)

# Test creating a record for HBNS (facility 37)
payload = {
    "year": 2022,
    "month": 1,
    "facility_id": 37,
    "process_type": "combustion",
    "fuel_type": "natural_gas",
    "quantity": 1000.0,
    "unit": "m3",
    "equipment_id": "TEST-HEATER-01",
    "group_name": "CPF",
    "factor_source": "default",
    "status": "Verified",
    "allow_duplicate": True
}
headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}
create_res = s.post("http://localhost:5000/api/emissions/", json=payload, headers=headers)
print("Create status:", create_res.status_code)
print("Create response:", create_res.text[:300])
