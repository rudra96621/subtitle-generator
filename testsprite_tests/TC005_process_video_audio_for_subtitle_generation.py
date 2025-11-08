import requests
import time

BASE_URL = "http://localhost:8501"
TIMEOUT = 30

def test_process_video_audio_for_subtitle_generation():
    # Step 1: Authenticate user to call /process endpoint (create user & login)
    session = requests.Session()
    user_data = {
        "full_name": "Test User TC005",
        "email": "testuser_tc005@example.com",
        "username": "testuser_tc005",
        "password": "StrongPass!234"
    }
    try:
        # Register user
        resp_signup = session.post(
            f"{BASE_URL}/signup",
            json={
                "full_name": user_data["full_name"],
                "email": user_data["email"],
                "username": user_data["username"],
                "password": user_data["password"]
            },
            timeout=TIMEOUT
        )
        assert resp_signup.status_code == 201 or resp_signup.status_code == 200, f"Signup failed: {resp_signup.text}"

        # Login user
        resp_login = session.post(
            f"{BASE_URL}/login",
            json={
                "username": user_data["username"],
                "password": user_data["password"]
            },
            timeout=TIMEOUT
        )
        assert resp_login.status_code == 200, f"Login failed: {resp_login.text}"
        if "token" in resp_login.json():
            token = resp_login.json()["token"]
            session.headers.update({"Authorization": f"Bearer {token}"})

        # Step 2: Upload a sample valid video/audio file for processing
        # Using a small silent audio sample as binary content (simulate upload)
        audio_content = b"\x52\x49\x46\x46\x24\x08\x00\x00\x57\x41\x56\x45\x66\x6D\x74\x20"  # small WAV header snippet

        files = {
            "file": ("test_audio.wav", audio_content, "audio/wav")
        }
        resp_upload = session.post(f"{BASE_URL}/upload", files=files, timeout=TIMEOUT)
        assert resp_upload.status_code == 200, f"Upload failed: {resp_upload.text}"
        upload_json = resp_upload.json()
        assert "file_id" in upload_json or "filename" in upload_json, "Upload response missing file identifier."

        # Step 3: Test /process endpoint with valid parameters
        # Verify various model_size and device enumeration options and edge cases
        process_payload = {
            "spoken_lang": "en",
            "target_lang": "es",
            "model_size": "medium",
            "device": "CPU"
        }
        resp_process = session.post(f"{BASE_URL}/process", json=process_payload, timeout=TIMEOUT)
        assert resp_process.status_code == 200, f"Process endpoint failed: {resp_process.text}"
        process_result = resp_process.json()

        # Validate keys and data structure in response
        # Expect transcription text, translated text, subtitles info
        assert "transcription" in process_result, "Response missing 'transcription'."
        assert isinstance(process_result["transcription"], str), "'transcription' should be string."
        assert "translation" in process_result, "Response missing 'translation'."
        assert isinstance(process_result["translation"], str), "'translation' should be string."
        assert "subtitles" in process_result, "Response missing 'subtitles'."
        assert isinstance(process_result["subtitles"], list), "'subtitles' should be a list."

        for item in process_result["subtitles"]:
            assert isinstance(item, dict), "Each subtitle should be a dict."
            assert "start" in item and isinstance(item["start"], (int, float)), "'start' missing or invalid."
            assert "end" in item and isinstance(item["end"], (int, float)), "'end' missing or invalid."
            assert "text" in item and isinstance(item["text"], str), "'text' missing or invalid."

        # Test edge cases: invalid model size
        invalid_payload = dict(process_payload)
        invalid_payload["model_size"] = "extra_large"
        resp_invalid = session.post(f"{BASE_URL}/process", json=invalid_payload, timeout=TIMEOUT)
        assert resp_invalid.status_code in [400, 422], "Invalid model_size should return client error."

        # Test edge cases: invalid device
        invalid_payload = dict(process_payload)
        invalid_payload["device"] = "QuantumProcessor"
        resp_invalid = session.post(f"{BASE_URL}/process", json=invalid_payload, timeout=TIMEOUT)
        assert resp_invalid.status_code in [400, 422], "Invalid device should return client error."

        # Test edge case: missing required fields
        incomplete_payload = {"spoken_lang": "en"}
        resp_incomplete = session.post(f"{BASE_URL}/process", json=incomplete_payload, timeout=TIMEOUT)
        assert resp_incomplete.status_code in [400, 422], "Missing fields should return client error."

        # Test security: injection in spoken_lang
        injection_payload = dict(process_payload)
        injection_payload["spoken_lang"] = "'; DROP TABLE users; --"
        resp_inject = session.post(f"{BASE_URL}/process", json=injection_payload, timeout=TIMEOUT)
        # Server should not execute injection but rather handle safely
        assert resp_inject.status_code in [400, 422], "Injection attempt should be rejected."

        # Performance: basic timing check for process endpoint with normal params
        start_time = time.time()
        resp_perf = session.post(f"{BASE_URL}/process", json=process_payload, timeout=TIMEOUT)
        duration = time.time() - start_time
        assert resp_perf.status_code == 200, f"Performance test process failed: {resp_perf.text}"
        # Check duration is reasonable (e.g., less than 60 seconds for medium model)
        assert duration < 60, f"Processing took too long: {duration} seconds"

    finally:
        # Cleanup: delete user to clear test data if delete user endpoint available
        del_resp = session.delete(f"{BASE_URL}/db/users", json={"username": user_data["username"]}, timeout=TIMEOUT)
        # Do not fail test on cleanup failure, but log if needed
        if del_resp.status_code not in [200, 204, 404]:
            print(f"Warning: could not delete test user, status {del_resp.status_code}")

test_process_video_audio_for_subtitle_generation()