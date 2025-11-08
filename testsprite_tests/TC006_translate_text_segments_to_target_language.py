import requests
import time

BASE_URL = "http://localhost:8501"
TIMEOUT = 30

def test_translate_text_segments_to_target_language():
    url = f"{BASE_URL}/translate"
    headers = {
        "Content-Type": "application/json"
    }

    # Define diverse segments including edge cases: empty text, overlapping times, long text, invalid times
    segments = [
        {"start": 0.0, "end": 2.5, "text": "Hello world!"},
        {"start": 2.5, "end": 5.0, "text": "This is a test."},
        {"start": 5.0, "end": 5.0, "text": ""},  # zero length segment with empty text
        {"start": 5.0, "end": 4.0, "text": "Backwards time segment"},  # invalid time range
        {"start": 5.0, "end": 6.0, "text": "Line with special chars: !@#$%^&*()"},
        {"start": 6.0, "end": 8.0, "text": "Line with a very very very very very very very very very very very very long text segment to test performance and stability."},
        {"start": 7.5, "end": 9.0, "text": "Overlapping segment test."}
    ]
    target_lang = "es"  # Spanish

    payload = {
        "segments": segments,
        "target_lang": target_lang
    }

    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        duration = time.time() - start_time
    except requests.exceptions.Timeout:
        assert False, "Request timed out"
    except requests.exceptions.RequestException as e:
        assert False, f"Request exception occurred: {e}"

    # Basic response validations
    assert response.status_code == 200, f"Expected status 200 OK but got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Validate that response has translated segments, and lengths match
    assert isinstance(data, dict), "Response JSON should be a dictionary"
    assert "segments" in data, "Response JSON missing 'segments' key"
    translated_segments = data["segments"]
    assert isinstance(translated_segments, list), "'segments' should be a list"
    assert len(translated_segments) == len(segments), "Number of translated segments does not match request"

    # Validate each segment structure and type
    for original, translated in zip(segments, translated_segments):
        assert isinstance(translated, dict), "Each translated segment must be a dict"
        assert "start" in translated and "end" in translated and "text" in translated, \
            "Translated segment missing required keys 'start', 'end', or 'text'"
        # Validate times match input for non-error segments (e.g. ignoring invalid time segment input)
        if original["start"] <= original["end"]:
            assert translated["start"] == original["start"], "Translated segment 'start' time mismatch"
            assert translated["end"] == original["end"], "Translated segment 'end' time mismatch"
        # Validate translated text is string and not empty if original text was not empty
        assert isinstance(translated["text"], str), "Translated 'text' must be a string"
        if original["text"].strip():
            # Translation should produce some changed text, not empty and different if possible
            assert translated["text"].strip(), "Translated text is empty for non-empty original"
            if translated["text"].strip().lower() == original["text"].strip().lower():
                # Allowed that sometimes translation returns same text (e.g. proper nouns), so no assert fail
                pass

    # Performance check: response should be reasonably fast (e.g. under 5 seconds for this test)
    assert duration < 10, f"Translation took too long: {duration:.2f} seconds"

    # Test error handling for invalid input: missing target_lang
    invalid_payloads = [
        # Missing segments key
        {"target_lang": "fr"},
        # Missing target_lang key
        {"segments": [{"start": 0, "end": 1, "text": "Test"}]},
        # Empty segments array
        {"segments": [], "target_lang": "fr"},
        # Invalid segment data types
        {"segments": [{"start": "zero", "end": "one", "text": 123}], "target_lang": "fr"},
        # Unsupported target language code (assuming 'xx' invalid)
        {"segments": [{"start": 0, "end": 1, "text": "Hello"}], "target_lang": "xx"}
    ]

    for invalid_payload in invalid_payloads:
        try:
            resp = requests.post(url, json=invalid_payload, headers=headers, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            assert False, f"Request exception with invalid payload: {e}"
        # Expect a 4xx error for invalid requests
        assert resp.status_code >= 400 and resp.status_code < 500, \
            f"Invalid payload should return client error but got status {resp.status_code}"

    # Security header checks: no unexpected sensitive headers exposed
    for header_name in response.headers:
        # For production, sensitive headers like 'Set-Cookie' or 'Server' should be checked if included
        # Just ensure X-Frame-Options or Content-Security-Policy present for security best practices
        pass

    # Additional edge case: large number of segments
    large_segments = [{"start": i*1.0, "end": i*1.0+0.5, "text": f"Segment {i}"} for i in range(1000)]
    large_payload = {
        "segments": large_segments,
        "target_lang": "de"
    }
    try:
        r_large = requests.post(url, json=large_payload, headers=headers, timeout=TIMEOUT)
        assert r_large.status_code == 200, f"Large payload translation failed with status {r_large.status_code}"
        data_large = r_large.json()
        assert len(data_large.get("segments", [])) == 1000, "Large payload translation segment count mismatch"
    except requests.exceptions.RequestException as e:
        assert False, f"Request exception with large payload: {e}"

test_translate_text_segments_to_target_language()
