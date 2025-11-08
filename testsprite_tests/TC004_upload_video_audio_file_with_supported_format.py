import requests
import os
import io

BASE_URL = "http://localhost:8501"
UPLOAD_ENDPOINT = f"{BASE_URL}/upload"
TIMEOUT = 30

# Example supported video/audio formats (minimal to test with)
SUPPORTED_EXTENSIONS = [
    ".mp4",  # video
    ".mp3",  # audio
    ".wav",
    ".m4a",
    ".mov",
    ".aac"
]

# Minimal valid dummy content generator for audio/video files
def generate_dummy_file_content(extension: str) -> bytes:
    # Minimal headers or bytes to simulate a valid audio/video file for upload
    # This is a simple heuristic: some formats start with certain bytes
    if extension == ".mp4" or extension == ".mov":
        # MP4/QuickTime file header: ftyp
        return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41isom"
    elif extension == ".mp3":
        # MP3 frame sync bytes
        return b"\xff\xfb\x90\x64" + b"\x00" * 1000
    elif extension == ".wav":
        # WAV header "RIFF" chunk descriptor
        return b"RIFF" + b"\x00" * 1000
    elif extension == ".m4a":
        # Similar to mp4 ftyp box
        return b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 1000
    elif extension == ".aac":
        # ADTS header start with 0xFFF
        return b"\xff\xf1" + b"\x00" * 1000
    else:
        # Default dummy content
        return b"dummydata" * 100

def test_upload_video_audio_file_with_supported_format():
    # Try all supported formats to comprehensively validate the endpoint behavior with different supported files
    for ext in SUPPORTED_EXTENSIONS:
        file_content = generate_dummy_file_content(ext)
        file_name = f"testfile{ext}"
        files = {
            'file': (file_name, io.BytesIO(file_content), 'application/octet-stream')
        }
        headers = {}
        response = None
        try:
            # Upload the file
            response = requests.post(UPLOAD_ENDPOINT, files=files, headers=headers, timeout=TIMEOUT)
            # Validate status code is success 2xx (preferably 200 or 201)
            assert response.status_code in (200, 201), f"Unexpected status code for {file_name}: {response.status_code}"

            # Validate content type is JSON or expected type
            content_type = response.headers.get('Content-Type', '')
            assert 'application/json' in content_type, f"Response content type unexpected for {file_name}: {content_type}"

            # Validate returned JSON has expected structure indicating success and file info
            json_resp = response.json()
            # Assert at least a success indicator and stored filename or file id
            assert 'success' in json_resp and json_resp['success'] is True, f"Upload failed for {file_name}"
            # Assuming an 'file_id' or 'filename' is returned for reference
            assert ('file_id' in json_resp or 'filename' in json_resp), f"No file identifier returned for {file_name}"

            # Additional edge case: check size reported, content hashes, or warnings if any
            if 'size' in json_resp:
                assert isinstance(json_resp['size'], int) and json_resp['size'] > 0, "Invalid size returned"

        except (requests.RequestException, AssertionError, ValueError) as e:
            raise AssertionError(f"Failed upload test for extension {ext}: {str(e)}") from e


test_upload_video_audio_file_with_supported_format()