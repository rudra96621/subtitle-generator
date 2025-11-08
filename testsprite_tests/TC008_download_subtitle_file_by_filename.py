import requests
import uuid
import time

BASE_URL = "http://localhost:8501"
DOWNLOAD_ENDPOINT = f"{BASE_URL}/download/srt"
UPLOAD_ENDPOINT = f"{BASE_URL}/upload"

TIMEOUT = 30

def test_download_subtitle_by_filename():
    # Generate a unique filename for the test subtitle file
    test_filename = f"test_subtitle_{uuid.uuid4().hex}.srt"
    test_file_content = """1
00:00:00,000 --> 00:00:01,000
Hello world!

"""

    # Step 1: Upload a subtitle file to be downloaded
    # Since the API does not explicitly provide a direct subtitle upload endpoint,
    # upload a dummy video/audio file, then simulate subtitle generation by uploading the subtitle file separately.
    # Assuming upload accepts any file for the demo purpose in this test.

    # Create a dummy text file to upload as subtitle (simulate upload file)
    try:
        files = {
            'file': (test_filename, test_file_content, 'application/x-subrip')
        }
        upload_response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=TIMEOUT)
        upload_response.raise_for_status()
        # Assuming the upload returns JSON with confirmation or file id - but no schema given
        # So, proceed assuming success means file stored for download

        # Step 2: Test downloading the subtitle file by filename
        params = {'filename': test_filename}
        download_response = requests.get(DOWNLOAD_ENDPOINT, params=params, timeout=TIMEOUT)
        # Response should be 200 and content is subtitle file
        assert download_response.status_code == 200, f"Expected 200 OK, got {download_response.status_code}"
        content_type = download_response.headers.get('Content-Type', '')
        # SRT content-type typical is 'application/x-subrip' or 'text/plain'
        assert content_type in ['application/x-subrip', 'text/plain', 'application/octet-stream'], f"Unexpected Content-Type: {content_type}"
        content_disposition = download_response.headers.get('Content-Disposition', '')
        assert test_filename in content_disposition, f"Filename {test_filename} not in Content-Disposition header"

        content = download_response.content.decode('utf-8')
        assert "Hello world!" in content, "Downloaded subtitle content does not contain expected text"

        # Edge case: filename with special characters
        special_filename = f"test_subtitle_äöü_{uuid.uuid4().hex}.srt"
        files_special = {
            'file': (special_filename, test_file_content, 'application/x-subrip')
        }
        upload_special_resp = requests.post(UPLOAD_ENDPOINT, files=files_special, timeout=TIMEOUT)
        upload_special_resp.raise_for_status()
        params_special = {'filename': special_filename}
        download_special_resp = requests.get(DOWNLOAD_ENDPOINT, params=params_special, timeout=TIMEOUT)
        assert download_special_resp.status_code == 200, f"Expected 200 OK for special filename, got {download_special_resp.status_code}"
        assert special_filename in download_special_resp.headers.get('Content-Disposition', ''), "Filename with special chars missing in header"
        assert "Hello world!" in download_special_resp.content.decode('utf-8'), "Subtitle content mismatch for special filename"

        # Negative test: missing filename parameter
        err_resp = requests.get(DOWNLOAD_ENDPOINT, timeout=TIMEOUT)
        assert err_resp.status_code in [400, 422], f"Expected 400 or 422 for missing filename, got {err_resp.status_code}"

        # Negative test: filename does not exist
        params_nonexistent = {'filename': 'nonexistent_file_1234567890.srt'}
        not_found_resp = requests.get(DOWNLOAD_ENDPOINT, params=params_nonexistent, timeout=TIMEOUT)
        # Assuming 404 or 400 if not found
        assert not_found_resp.status_code in [404, 400], f"Expected 404 or 400 for nonexistent filename, got {not_found_resp.status_code}"

        # Security test: Path traversal attempt
        dangerous_filename = "../../etc/passwd"
        params_danger = {'filename': dangerous_filename}
        danger_resp = requests.get(DOWNLOAD_ENDPOINT, params=params_danger, timeout=TIMEOUT)
        # Should reject or sanitize the filename
        assert danger_resp.status_code in [400, 403, 404], f"Expected 400/403/404 for path traversal attempt, got {danger_resp.status_code}"

        # Performance: Measure response time for valid request
        start_time = time.time()
        perf_resp = requests.get(DOWNLOAD_ENDPOINT, params=params, timeout=TIMEOUT)
        duration = time.time() - start_time
        assert perf_resp.status_code == 200, f"Performance test: Expected 200 OK, got {perf_resp.status_code}"
        assert duration < 5, f"Performance test: Download took too long {duration:.2f} seconds"

    finally:
        # Cleanup: If API had a delete or cleanup endpoint, call it here to remove test files
        # No such endpoint defined in PRD for deleting individual files
        # So cannot clean up uploaded test files via API - would require DB cleanup outside this test
        pass


test_download_subtitle_by_filename()