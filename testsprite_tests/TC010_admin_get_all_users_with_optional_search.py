import requests
import time

BASE_URL = "http://localhost:8501"
ADMIN_USERS_ENDPOINT = f"{BASE_URL}/admin/users"
LOGIN_ENDPOINT = f"{BASE_URL}/login"
SIGNUP_ENDPOINT = f"{BASE_URL}/signup"
DELETE_USER_ENDPOINT = f"{BASE_URL}/admin/users/{{username}}"

# Credentials for a test admin user (adjust accordingly or create dynamically)
ADMIN_CREDENTIALS = {
    "username": "testadminuser",
    "password": "AdminPass123!"
}

def create_test_admin_user():
    # Try to create a test admin user for authentication, ignore if exists
    signup_payload = {
        "full_name": "Test Admin",
        "email": "testadmin@example.com",
        "username": ADMIN_CREDENTIALS["username"],
        "password": ADMIN_CREDENTIALS["password"]
    }
    try:
        resp = requests.post(SIGNUP_ENDPOINT, json=signup_payload, timeout=30)
        # 201 Created or 409 Conflict (user exists) acceptable
        if resp.status_code not in [201, 409]:
            resp.raise_for_status()
    except Exception as e:
        # Log or pass if user already exists for test continuity
        pass

def login_admin():
    resp = requests.post(LOGIN_ENDPOINT, json=ADMIN_CREDENTIALS, timeout=30)
    resp.raise_for_status()
    token = resp.json().get("access_token") or resp.json().get("token")  # token key depends on implementation
    if not token:
        raise RuntimeError("Admin login failed: no token returned")
    return token

def delete_test_admin_user(username, headers):
    # Clean up test user if needed
    url = DELETE_USER_ENDPOINT.format(username=username)
    try:
        resp = requests.delete(url, headers=headers, timeout=30)
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()
    except Exception:
        pass  # best effort cleanup

def test_admin_get_all_users_with_optional_search():
    create_test_admin_user()
    token = login_admin()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 1. Test without search parameter (get all users)
        resp = requests.get(ADMIN_USERS_ENDPOINT, headers=headers, timeout=30)
        assert resp.status_code == 200, f"Expected 200 OK but got {resp.status_code}"
        users = resp.json()
        assert isinstance(users, list), "Response without search should be a list"
        usernames = {u.get("username") for u in users if isinstance(u, dict) and "username" in u}
        assert len(users) >= 1, "User list should contain at least one user (admin user present)"

        # 2. Test with search parameter that matches a username partially
        if usernames:
            sample_username = next(iter(usernames))
            # Take a substring to test partial search
            search_query = sample_username[:3]
            resp_search = requests.get(ADMIN_USERS_ENDPOINT, headers=headers, params={"search": search_query}, timeout=30)
            assert resp_search.status_code == 200, f"Expected 200 OK but got {resp_search.status_code} for search query"
            filtered_users = resp_search.json()
            assert isinstance(filtered_users, list), "Response with search should be a list"
            assert any(search_query.lower() in u.get("username", "").lower() for u in filtered_users), "Filtered users should contain search query"

            # Test empty list behavior for a search that unlikely matches
            unlikely_search = "no_such_user_1234567890"
            resp_none = requests.get(ADMIN_USERS_ENDPOINT, headers=headers, params={"search": unlikely_search}, timeout=30)
            assert resp_none.status_code == 200, f"Expected 200 OK but got {resp_none.status_code} for unlikely search"
            assert resp_none.json() == [], "Search with no match should return empty list"

        # 3. Test input validation: search with special chars and unicode
        special_searches = ["!@#$%^&*()", "测试", "ユーザー"]
        for s in special_searches:
            resp_special = requests.get(ADMIN_USERS_ENDPOINT, headers=headers, params={"search": s}, timeout=30)
            assert resp_special.status_code == 200, f"Expected 200 OK but got {resp_special.status_code} for special search {s}"
            assert isinstance(resp_special.json(), list), f"Response for special search {s} should be a list"

        # 4. Test error handling: invalid auth token
        bad_headers = {"Authorization": "Bearer invalidtoken123"}
        resp_unauth = requests.get(ADMIN_USERS_ENDPOINT, headers=bad_headers, timeout=30)
        assert resp_unauth.status_code in (401, 403), "Invalid token should cause 401 Unauthorized or 403 Forbidden"

        # 5. Performance - measure response time for a request
        start = time.time()
        resp_perf = requests.get(ADMIN_USERS_ENDPOINT, headers=headers, timeout=30)
        elapsed = time.time() - start
        assert resp_perf.status_code == 200, "Performance test request failed"
        assert elapsed < 5.0, f"Response time {elapsed}s exceeds threshold for production"
    finally:
        # No test user deletion here as admin user may be persistent
        pass


test_admin_get_all_users_with_optional_search()