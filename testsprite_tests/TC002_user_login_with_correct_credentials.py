import requests
import time
import random
import string

BASE_URL = "http://localhost:8501"
TIMEOUT = 30

def generate_random_user():
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return {
        "full_name": f"Test User {suffix}",
        "email": f"testuser{suffix}@example.com",
        "username": f"testuser{suffix}",
        "password": "StrongP@ssw0rd!"
    }

def test_user_login_with_correct_credentials():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}
    user = generate_random_user()

    # Register new user for login test
    signup_url = f"{BASE_URL}/signup"
    login_url = f"{BASE_URL}/login"
    delete_user_url = f"{BASE_URL}/admin/users/{user['username']}"
    try:
        # Create user
        resp_signup = session.post(signup_url, json=user, headers=headers, timeout=TIMEOUT)
        assert resp_signup.status_code == 201 or resp_signup.status_code == 200, f"User signup failed: {resp_signup.text}"

        # Wait briefly to ensure user is ready for login
        time.sleep(0.5)

        # Test login with correct credentials
        login_payload = {
            "username": user["username"],
            "password": user["password"]
        }
        resp_login = session.post(login_url, json=login_payload, headers=headers, timeout=TIMEOUT)

        # Validate response code and body structure
        assert resp_login.status_code == 200, f"Login failed with status code {resp_login.status_code}: {resp_login.text}"
        json_resp = resp_login.json()
        assert "token" in json_resp or "session_id" in json_resp or "message" in json_resp, "Login response missing expected fields"

        # Validate that the token/session is non-empty if present
        if "token" in json_resp:
            assert isinstance(json_resp["token"], str) and json_resp["token"], "Empty token received"
        if "session_id" in json_resp:
            assert isinstance(json_resp["session_id"], str) and json_resp["session_id"], "Empty session_id received"

        # Additional edge case: login with extra fields ignored by the API
        extended_payload = {
            "username": user["username"],
            "password": user["password"],
            "unexpected_field": "unexpected_value"
        }
        resp_ext = session.post(login_url, json=extended_payload, headers=headers, timeout=TIMEOUT)
        assert resp_ext.status_code == 200, "Login failed with unexpected extra fields"
        resp_ext_json = resp_ext.json()
        assert "token" in resp_ext_json or "session_id" in resp_ext_json, "Login with extra fields missing token/session_id"

        # Security edge case: login with password having SQL injection pattern
        sql_injection_payload = {
            "username": user["username"],
            "password": "' OR '1'='1"
        }
        resp_sql = session.post(login_url, json=sql_injection_payload, headers=headers, timeout=TIMEOUT)
        assert resp_sql.status_code in (400,401), "Login should fail on SQL injection attempt"

        # Performance check: time taken for login should be reasonable (<5 seconds)
        start_perf = time.time()
        resp_perf = session.post(login_url, json=login_payload, headers=headers, timeout=TIMEOUT)
        elapsed = time.time() - start_perf
        assert elapsed < 5, f"Login took too long: {elapsed}s"

    finally:
        # Cleanup: delete the created user (assuming admin endpoint available for test cleanup)
        try:
            resp_del = session.delete(delete_user_url, headers=headers, timeout=TIMEOUT)
            # Accept both 200 OK and 204 No Content as success
            if resp_del.status_code not in (200, 204, 404):
                print(f"Warning: unexpected status on user delete {resp_del.status_code}: {resp_del.text}")
        except Exception as e:
            print(f"Exception during cleanup user delete: {e}")

test_user_login_with_correct_credentials()