import requests
import uuid

BASE_URL = "http://localhost:8501"
TIMEOUT = 30

def test_password_reset_with_matching_new_passwords():
    # Step 1: Create a test user to perform password reset
    signup_url = f"{BASE_URL}/signup"
    login_url = f"{BASE_URL}/login"
    reset_password_url = f"{BASE_URL}/reset_password"

    test_username = f"testuser_{uuid.uuid4().hex[:8]}"
    original_password = "OrigPass!1234"
    new_password = "NewPass!5678"

    headers = {"Content-Type": "application/json"}

    # Register user
    signup_payload = {
        "full_name": "Test User",
        "email": f"{test_username}@example.com",
        "username": test_username,
        "password": original_password
    }
    try:
        signup_resp = requests.post(signup_url, json=signup_payload, headers=headers, timeout=TIMEOUT)
        assert signup_resp.status_code == 201 or signup_resp.status_code == 200, f"Signup failed: {signup_resp.status_code} {signup_resp.text}"

        # Step 2: Password reset with matching new_password and confirm_password
        reset_payload = {
            "username": test_username,
            "new_password": new_password,
            "confirm_password": new_password
        }
        reset_resp = requests.post(reset_password_url, json=reset_payload, headers=headers, timeout=TIMEOUT)
        assert reset_resp.status_code == 200, f"Password reset failed with status {reset_resp.status_code}: {reset_resp.text}"
        reset_json = reset_resp.json()
        # Expect some success indication, either a message or a success flag
        assert ("success" in reset_json and reset_json["success"] is True) or ("message" in reset_json), "Password reset response missing success indication"

        # Step 3: Try logging in with the new password to verify password updated
        login_payload = {
            "username": test_username,
            "password": new_password
        }
        login_resp = requests.post(login_url, json=login_payload, headers=headers, timeout=TIMEOUT)
        assert login_resp.status_code == 200, f"Login after password reset failed: {login_resp.status_code} {login_resp.text}"
        # Expect token or success message
        login_json = login_resp.json()
        assert "token" in login_json or "success" in login_json, "Login response missing token or success indication"

        # Additional security checks: attempting password reset with blank/new_password edge case
        bad_payload = {
            "username": test_username,
            "new_password": "",
            "confirm_password": ""
        }
        bad_resp = requests.post(reset_password_url, json=bad_payload, headers=headers, timeout=TIMEOUT)
        assert bad_resp.status_code == 400 or bad_resp.status_code == 422, "Expected error status code for empty passwords"
        bad_json = bad_resp.json()
        assert "error" in bad_json or "message" in bad_json, "Error response missing error message for blank passwords"
        
        # Trying mismatched new_password and confirm_password
        mismatch_payload = {
            "username": test_username,
            "new_password": "password1",
            "confirm_password": "password2"
        }
        mismatch_resp = requests.post(reset_password_url, json=mismatch_payload, headers=headers, timeout=TIMEOUT)
        assert mismatch_resp.status_code == 400 or mismatch_resp.status_code == 422, "Expected error status for mismatched passwords"
        mismatch_json = mismatch_resp.json()
        assert "error" in mismatch_json or "message" in mismatch_json, "Error response missing error message for mismatched passwords"

    finally:
        # Clean up: delete the test user if an admin endpoint or DB operation is available
        # Attempt to delete user via admin panel or database operation
        del_user_url = f"{BASE_URL}/admin/users/{test_username}"
        try:
            del_resp = requests.delete(del_user_url, timeout=TIMEOUT)
            # Accept 200 or 204 as success, 404 means probably already deleted
            assert del_resp.status_code in (200, 204, 404), f"Failed to delete test user: {del_resp.status_code} {del_resp.text}"
        except Exception:
            pass  # Best effort cleanup

test_password_reset_with_matching_new_passwords()