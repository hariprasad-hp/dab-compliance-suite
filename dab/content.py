from time import sleep
from dab_tester import YesNoQuestion, Default_Validations
import jsons
from schema import dab_response_validator

_last_discovered_entry_id = None

def _has_invalid_entry_whitespace(response, test_result) -> bool:
    entries = response.get("entries") if isinstance(response, dict) else None
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for fld in ("entryId", "appId", "poster"):
            val = entry.get(fld)
            if not isinstance(val, str) or not val or any(ch.isspace() for ch in val):
                if getattr(test_result, "logs", None) is not None:
                    test_result.logs.append(f"[FAILED] content entry '{fld}' contains whitespace/empty: {val!r}")
                return True
    return False

def _cache_first_entry_id(response):
    """Cache the first valid entryId from content/search or content/recommendations for content/open."""
    global _last_discovered_entry_id
    entries = response.get("entries") if isinstance(response, dict) else None
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("entryId"), str) and entry["entryId"].strip():
                _last_discovered_entry_id = entry["entryId"].strip()
                break

def get_open_entry_id():
    """Return a device-advertised entryId when available, falling back to the sample UUID."""
    return _last_discovered_entry_id or "b8884dfa-60e8-448a-99f3-bcf283dcc903"

def open(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_content_open_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def search(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_content_search_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    if _has_invalid_entry_whitespace(response, test_result):
        return False
    if _has_invalid_entry_whitespace(response, test_result):
        return False
    _cache_first_entry_id(response)
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def recommendations(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_content_recommendations_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    if _has_invalid_entry_whitespace(response, test_result):
        return False
    _cache_first_entry_id(response)
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)
