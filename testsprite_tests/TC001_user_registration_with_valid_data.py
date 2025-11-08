import requests
import uuid
import traceback

BASE_URL = "http://localhost:8501"
SIGNUP_ENDPOINT = f"{BASE_URL}/signup"
DELETE_USER_ENDPOINT_TEMPLATE = f"{BASE_URL}/admin/users/{{username}}"

def test_user_registration_with_valid_data():
    # Generate unique user data for the test to avoid conflicts and ensure idempotency
    unique_suffix = str(uuid.uuid4())[:8]
    test_user = {
        "full_name": f"Test User {unique_suffix}",
        "email": f"testuser{unique_suffix}@example.com",
        "username": f"testuser{unique_suffix}",
        "password": "StrongPass!2025"
    }
    headers = {
        "Content-Type": "application/json"
    }
    created = False
    try:
        # Perform the signup request with valid user data
        response = requests.post(
            SIGNUP_ENDPOINT,
            json=test_user,
            headers=headers,
            timeout=30
        )
        # Assert HTTP status code for successful creation (commonly 201 or 200)
        assert response.status_code in (200, 201), f"Unexpected status code: {response.status_code}, Response: {response.text}"

        # Validate response content structure: expect JSON with success confirmation or user data (cannot assume exact schema but check basics)
        try:
            data = response.json()
        except Exception as e:
            assert False, f"Response not valid JSON: {response.text}"

        # Basic validations on returned JSON fields for robustness
        assert isinstance(data, dict), f"Expected response body to be dict, got {type(data)}"

        # Check if there is an indication of success or user info
        # Accept keys like 'message', 'user', 'username', 'id', etc.
        keys = data.keys()
        assert any(k in keys for k in ["username", "user", "message", "id"]), "Response JSON missing expected keys."

        # Security checks - password or sensitive info must NOT be returned
        sensitive_fields = ['password', 'pwd', 'pass']
        for field in sensitive_fields:
            assert field not in data, f"Sensitive field {field} found in response"

        created = True

        # Additional edge test: ensure returned username/email matches sent
        if "username" in data:
            assert data["username"] == test_user["username"], "Returned username does not match sent username"
        elif "user" in data and isinstance(data["user"], dict):
            assert data["user"].get("username") == test_user["username"], "Returned user.username does not match sent username"

    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {str(e)}"
    except AssertionError:
        # Reraise for test framework reporting
        raise
    except Exception:
        traceback.print_exc()
        assert False, "Unexpected error during test execution"

    finally:
        # Cleanup: Delete the created user to keep testing environment clean
        if created:
            try:
                delete_url = DELETE_USER_ENDPOINT_TEMPLATE.format(username=test_user["username"])
                del_response = requests.delete(delete_url, timeout=30)
                # Accept 200 or 204 as successful deletion responses
                assert del_response.status_code in (200, 204), f"User deletion failed with status {del_response.status_code}"
            except Exception:
                # Log cleanup failure but do not fail test because registration succeeded
                traceback.print_exc()

test_user_registration_with_valid_data()