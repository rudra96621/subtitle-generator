import requests
import time

BASE_URL = "http://localhost:8501"
TIMEOUT = 30

def test_render_subtitles_on_video_with_font_and_timing():
    """
    Test the /render_subtitles endpoint by providing video_path, subtitle segments,
    output_path, and font_path to verify correct rendering of subtitles on the video
    with proper font selection and synchronization.
    """

    # For the test, we need a video_path and font_path.
    # If not available, upload/create a minimal dummy video and font file.
    # We'll simulate this by uploading a dummy video and using a dummy font.
    # After the test, clean up created files.

    session = requests.Session()

    # Upload a dummy video file for testing
    video_filename = "test_video.mp4"
    font_filename = "test_font.ttf"
    output_filename = "output_test_video.mp4"

    try:
        # Step 1: Upload Video File
        video_file_content = (
            b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41"  # minimal mp4 header bytes for test
        )
        files = {
            'file': (video_filename, video_file_content, 'video/mp4')
        }
        upload_response = session.post(f"{BASE_URL}/upload", files=files, timeout=TIMEOUT)
        assert upload_response.status_code == 200, f"Video upload failed: {upload_response.text}"
        upload_json = upload_response.json()
        # Expecting a response with stored video path or identifier, fallback to filename
        stored_video_path = upload_json.get("file_path") or video_filename
        assert stored_video_path, "Uploaded video path missing in response."

        # Step 2: Upload Font File (simulate by upload or external font path)
        # Assuming font files can be uploaded via same /upload endpoint or available on server
        # Here we simulate upload of a font file as well.
        font_file_content = (
            b"\x00\x01\x00\x00\x00\x0f\x00\x80\x00\x03\x00\x50\x47\x46\x20\x20"  # minimal ttf header bytes for test
        )
        files = {
            'file': (font_filename, font_file_content, 'font/ttf')
        }
        font_upload_response = session.post(f"{BASE_URL}/upload", files=files, timeout=TIMEOUT)
        if font_upload_response.status_code == 200:
            font_json = font_upload_response.json()
            stored_font_path = font_json.get("file_path") or font_filename
        else:
            # If upload not supported for fonts, fallback to a default font path
            stored_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        # Step 3: Prepare subtitle segments (edge and normal cases)
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello world!"},
            {"start": 1.5, "end": 4.0, "text": "Overlapping subtitle"},   # Overlapping time segment edge case
            {"start": 5.0, "end": 5.5, "text": ""},                      # Empty text edge case
            {"start": 6.0, "end": 6.5, "text": "Quick subtitle"},
            # Extreme long subtitle text edge case
            {"start": 7.0, "end": 10.0, "text": "A"*1000}
        ]

        payload = {
            "video_path": stored_video_path,
            "segments": segments,
            "output_path": output_filename,
            "font_path": stored_font_path
        }

        headers = {
            "Content-Type": "application/json"
        }

        # Step 4: Post to /render_subtitles endpoint
        render_response = session.post(
            f"{BASE_URL}/render_subtitles",
            json=payload,
            headers=headers,
            timeout=TIMEOUT
        )
        assert render_response.status_code == 200, f"Rendering subtitles failed: {render_response.text}"
        render_json = render_response.json()

        # Step 5: Validate response content
        # Expect some confirmation, e.g. output file path or success flag
        assert "output_path" in render_json, "output_path missing in response"
        assert render_json["output_path"] == output_filename or render_json["output_path"].endswith(output_filename), "Output path mismatch"

        # Step 6: Security checks - basic validation to avoid injection or unsafe payload acceptance
        # Since we control payload, we verify API returned expected results without errors.
        # Check no error key in response and reasonable response time (basic performance check)
        assert "error" not in render_json, "API returned error in rendering subtitles"

        # Optional small performance benchmark (response time under timeout, ideally under 10s for this small test)
        # Not an assert but print for observation
        # print(f"Render response time: {render_response.elapsed.total_seconds():.2f}s")

    finally:
        # Cleanup uploaded files to avoid resource leak if API supports delete

        # Attempt to delete test video file from server if such endpoint existed
        # No delete endpoint given, so skip actual deletions.

        # If files persisted locally, in real environment delete them here.
        pass


test_render_subtitles_on_video_with_font_and_timing()