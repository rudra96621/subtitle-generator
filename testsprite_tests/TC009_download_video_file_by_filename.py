import requests
import os
import time

BASE_URL = "http://localhost:8501"
TIMEOUT = 30

def test_download_video_file_by_filename():
    # Preparations: upload a small dummy video file to have a file to download
    upload_url = f"{BASE_URL}/upload"
    download_url = f"{BASE_URL}/download/video"

    # Create a small dummy video file (1 second, black frame) for test
    dummy_video_path = "test_dummy_video.mp4"
    downloaded_path = "downloaded_test_dummy_video.mp4"
    try:
        # Generate dummy video file using ffmpeg if available
        if not os.path.exists(dummy_video_path):
            import subprocess
            try:
                subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                cmd = [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1", 
                    "-pix_fmt", "yuv420p", dummy_video_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # ffmpeg not available; create small dummy binary file instead
                with open(dummy_video_path, "wb") as f:
                    f.write(b"\x00" * 1024)  # 1KB dummy content

        with open(dummy_video_path, "rb") as f:
            files = {'file': ("test_dummy_video.mp4", f, "video/mp4")}
            r_upload = requests.post(upload_url, files=files, timeout=TIMEOUT)
        assert r_upload.status_code == 200, f"Upload failed with status {r_upload.status_code}"
        
        # Extract filename from upload response if provided, else use original filename
        filename = None
        try:
            if r_upload.headers.get('Content-Type','').startswith('application/json'):
                resp_json = r_upload.json()
                # Look for 'filename' or similar in response to get stored filename
                if 'filename' in resp_json:
                    filename = resp_json['filename']
                elif 'file_name' in resp_json:
                    filename = resp_json['file_name']
        except Exception:
            pass
        if not filename:
            filename = "test_dummy_video.mp4"

        # Wait briefly in case file processing/storage is async
        time.sleep(1)

        # Test: Download the video file by filename
        params = {'filename': filename}
        r_download = requests.get(download_url, params=params, timeout=TIMEOUT)
        
        # Successful response checks
        assert r_download.status_code == 200, f"Download failed with status {r_download.status_code}"
        content_type = r_download.headers.get('Content-Type', '')
        assert 'video' in content_type, f"Expected video content-type, got {content_type}"
        content_disp = r_download.headers.get('Content-Disposition', '')
        assert filename in content_disp or filename in r_download.url, "Filename not found in Content-Disposition or URL"

        # Check content length reasonable (>0 and matches uploaded file size roughly)
        content_length = r_download.headers.get('Content-Length')
        if content_length is not None:
            size = int(content_length)
            assert size > 0, "Downloaded content length is zero"
            uploaded_file_size = os.path.getsize(dummy_video_path)
            # Allow some tolerance for any compression or metadata changes
            assert abs(size - uploaded_file_size) < uploaded_file_size * 0.5, \
                f"Downloaded file size {size} differs significantly from uploaded size {uploaded_file_size}"

        # Try saving downloaded content to verify file is valid video format
        with open(downloaded_path, "wb") as f:
            f.write(r_download.content)

        # Quick validation: check if downloaded file size > 0 and is non-empty
        assert os.path.getsize(downloaded_path) > 0, "Downloaded video file is empty"

        # Optionally, run ffprobe or similar to verify video file integrity (if ffprobe installed)
        try:
            import subprocess
            probe = subprocess.run(
                ["ffprobe", "-v", "error", downloaded_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            assert probe.returncode == 0, f"Downloaded file failed ffprobe check: {probe.stderr.decode()}"
        except FileNotFoundError:
            # ffprobe not installed, skip this validation
            pass

    finally:
        # Cleanup: delete uploaded file if API exists, and remove local files
        # No delete endpoint provided in PRD for uploaded files, so just remove local files
        for fpath in [dummy_video_path, downloaded_path]:
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
            except Exception:
                pass

test_download_video_file_by_filename()