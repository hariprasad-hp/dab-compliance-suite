from time import sleep
from dab_tester import YesNoQuestion, Default_Validations
import jsons
from schema import (
    dab_response_validator,
    list_system_settings_schema_20,
    list_system_settings_schema_21,
    system_settings_schema,
    system_settings_schema_21,
    MATCH_CONTENT_FRAME_RATE_ENUM,
    HDR_OUTPUT_MODE_ENUM,
    PICTURE_MODE_ENUM,
    AUDIO_OUTPUT_MODE_ENUM,
    AUDIO_OUTPUT_SOURCE_ENUM_20,
    AUDIO_OUTPUT_SOURCE_ENUM_21,
    VIDEO_INPUT_SOURCE_ENUM_20,
    VIDEO_INPUT_SOURCE_ENUM_21,
    find_whitespace_violations,
)
from util.enforcement_manager import EnforcementManager
from logger import LOGGER
import dab_tester

def restart(test_result, durationInMs=0,expectedLatencyMs=0):
    """Validate system/restart response, confirm reboot, and record operation latency."""
    try:
        dab_response_validator.validate_dab_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    LOGGER.info("system/restart issued. Device will reboot; subsequent preflight health-check will wait for readiness.")
    q_ok = YesNoQuestion(test_result, "Device re-started?")
    lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)
    return q_ok and lat_ok

def _log_validation_error(test_result, msg):
    """Record a concise validation failure in both console output and TestResult.logs."""
    LOGGER.warn(msg)
    if getattr(test_result, "logs", None) is not None:
        test_result.logs.append(msg)

def _log_validation_warn(test_result, msg):
    """Record a non-blocking partner compatibility warning in console output and TestResult.logs."""
    LOGGER.warn(msg)
    if getattr(test_result, "logs", None) is not None:
        test_result.logs.append(msg)

def _schema_err(error):
    """Extract the one-line jsonschema error message without dumping the full schema dict."""
    return getattr(error, "message", str(error))

def settings_get(test_result, durationInMs=0,expectedLatencyMs=0):
    """Validate system/settings/get types, warn on extra keys, and verify consistency with settings/list."""
    try:
        dab_response_validator.validate_get_system_settings_response_schema(test_result.response)
    except Exception as error:
        _log_validation_error(test_result, f"[FAILED] system/settings/get schema error: {_schema_err(error)}")
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    ws_issues = find_whitespace_violations(response)
    if ws_issues:
        _log_validation_error(test_result, f"[FAILED] system/settings/get invalid whitespace: {ws_issues[0]}")
        return False

    version = getattr(dab_tester, "DAB_VERSION", None) or "2.0"
    known_get_keys = set((system_settings_schema_21 if version >= "2.1" else system_settings_schema).keys()) | {"error"}
    extra_get = sorted(k for k in response.keys() if k not in known_get_keys)
    if extra_get:
        _log_validation_warn(
            test_result,
            f"[WARN] system/settings/get includes extra/partner key(s) not in DAB {version} SystemSettings: {extra_get}",
        )

    # Cross-validate current values against cached system/settings/list capabilities if available
    sup = EnforcementManager().get_supported_settings()
    if isinstance(sup, dict) and sup.get("status") == 200:
        known_list_keys = set((list_system_settings_schema_21 if version >= "2.1" else list_system_settings_schema_20)["properties"].keys())
        for key, desc in sup.items():
            if key in ("status", "error", "statusText", "ts", "screenSaverMinTimeout") or key not in known_list_keys:
                continue
            if isinstance(desc, bool) and desc is True:
                if key not in response:
                    _log_validation_error(test_result, f"[FAILED] system/settings/get missing supported setting '{key}' advertised in settings/list.")
                    return False
                if key == "screenSaver" and version >= "2.1":
                    if "screenSaverTimeout" not in response:
                        _log_validation_error(test_result, "[FAILED] system/settings/get missing 'screenSaverTimeout' while 'screenSaver' is true.")
                        return False
                    min_to = sup.get("screenSaverMinTimeout", 0)
                    if not isinstance(min_to, bool) and isinstance(min_to, (int, float)) and response["screenSaverTimeout"] < min_to:
                        _log_validation_error(test_result, f"[FAILED] screenSaverTimeout ({response['screenSaverTimeout']}) < screenSaverMinTimeout ({min_to}).")
                        return False
            elif isinstance(desc, list) and len(desc) > 0:
                if key not in response:
                    _log_validation_error(test_result, f"[FAILED] system/settings/get missing supported setting '{key}' advertised in settings/list.")
                    return False
                val = response[key]
                if isinstance(desc[0], dict):
                    if not isinstance(val, dict) or not any(all(val.get(fk) == opt.get(fk) for fk in opt) for opt in desc):
                        _log_validation_error(test_result, f"[FAILED] system/settings/get '{key}' value {val} not in settings/list options.")
                        return False
                elif val not in desc:
                    _log_validation_error(test_result, f"[FAILED] system/settings/get '{key}' value {val!r} not in settings/list options {desc}.")
                    return False
            elif isinstance(desc, dict) and {"min", "max"}.issubset(desc.keys()) and desc["min"] < desc["max"]:
                if key not in response:
                    _log_validation_error(test_result, f"[FAILED] system/settings/get missing supported setting '{key}' advertised in settings/list.")
                    return False
                val = response[key]
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not (desc["min"] <= val <= desc["max"]):
                    _log_validation_error(test_result, f"[FAILED] system/settings/get '{key}' value {val!r} outside range [{desc['min']}, {desc['max']}].")
                    return False

    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def settings_set(test_result, durationInMs=0,expectedLatencyMs=0):
    """Validate system/settings/set schema and verify the updated setting key is echoed in the response."""
    try:
        dab_response_validator.validate_set_system_settings_response_schema(test_result.response)
    except Exception as error:
        _log_validation_error(test_result, f"[FAILED] system/settings/set schema error: {_schema_err(error)}")
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    ws_issues = find_whitespace_violations(response)
    if ws_issues:
        _log_validation_error(test_result, f"[FAILED] system/settings/set invalid whitespace: {ws_issues[0]}")
        return False
    try:
        req = jsons.loads(test_result.request) if isinstance(test_result.request, str) else test_result.request
        if isinstance(req, dict) and len(req) == 1:
            req_key, req_val = next(iter(req.items()))
            if req_key not in response:
                _log_validation_error(test_result, f"[FAILED] SetSystemSettingsResponse did not return updated key '{req_key}'.")
                return False
            if response[req_key] != req_val:
                _log_validation_error(
                    test_result,
                    f"[FAILED] SetSystemSettingsResponse echoed {req_key}={response[req_key]!r}, expected {req_val!r}.",
                )
                return False
    except Exception:
        pass
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def settings_list(test_result, durationInMs=0, expectedLatencyMs=0):
    """Validate settings/list types, prompt acknowledgment for unsupported claims, and check latency."""
    try:
        response = jsons.loads(test_result.response)
    except Exception as error:
        _log_validation_error(test_result, f"system/settings/list: JSON parse error: {error}")
        EnforcementManager().set_supported_settings(None)
        return False

    # Update supported settings map so downstream capability checks have device state
    EnforcementManager().set_supported_settings(response)

    status = response.get("status")
    if status != 200:
        _log_validation_error(test_result, f"system/settings/list returned status {status}.")
        return False

    try:
        dab_response_validator.validate_list_system_settings_schema(test_result.response)
    except Exception as error:
        _log_validation_error(test_result, f"[FAILED] system/settings/list schema error: {_schema_err(error)}")
        return False

    ws_issues = find_whitespace_violations(response)
    if ws_issues:
        _log_validation_error(test_result, f"[FAILED] system/settings/list invalid whitespace: {ws_issues[0]}")
        return False

    version = getattr(dab_tester, "DAB_VERSION", None) or "2.0"
    target_schema = list_system_settings_schema_21 if version >= "2.1" else list_system_settings_schema_20
    expected_keys = [k for k in target_schema["properties"] if k not in ("status", "error")]

    # Collect all settings the device claims as unsupported (omitted, false, empty [], or min >= max)
    unsupported_items = []
    for key in expected_keys:
        if key == "screenSaverMinTimeout" and response.get("screenSaver") is not True:
            continue
        if key not in response:
            unsupported_items.append(f"{key} (omitted)")
        else:
            desc = response[key]
            if isinstance(desc, bool) and desc is False:
                unsupported_items.append(f"{key} (false)")
            elif isinstance(desc, list) and len(desc) == 0:
                unsupported_items.append(f"{key} ([])")
            elif isinstance(desc, dict) and {"min", "max"}.issubset(desc.keys()) and desc["min"] >= desc["max"]:
                unsupported_items.append(f"{key} (min={desc['min']}, max={desc['max']})")

    extra_keys = sorted(k for k in response.keys() if k not in target_schema["properties"])
    if extra_keys:
        _log_validation_warn(
            test_result,
            f"[WARN] system/settings/list ({version}) includes extra/partner setting key(s): {extra_keys}",
        )

    spec_enums = {
        "matchContentFrameRate": set(MATCH_CONTENT_FRAME_RATE_ENUM),
        "hdrOutputMode": set(HDR_OUTPUT_MODE_ENUM),
        "pictureMode": set(PICTURE_MODE_ENUM),
        "audioOutputMode": set(AUDIO_OUTPUT_MODE_ENUM),
        "audioOutputSource": set(AUDIO_OUTPUT_SOURCE_ENUM_21 if version >= "2.1" else AUDIO_OUTPUT_SOURCE_ENUM_20),
        "videoInputSource": set(VIDEO_INPUT_SOURCE_ENUM_21 if version >= "2.1" else VIDEO_INPUT_SOURCE_ENUM_20),
    }
    for enum_key, allowed in spec_enums.items():
        vals = response.get(enum_key)
        if isinstance(vals, list):
            custom_vals = [v for v in vals if v not in allowed]
            if custom_vals:
                _log_validation_warn(
                    test_result,
                    f"[WARN] system/settings/list '{enum_key}' uses partner-specific option name(s): {custom_vals}",
                )

    sleep(0.1)
    lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)
    ack_fn = getattr(dab_tester, "AcknowledgeUnsupported", None)
    ack_ok = True
    if unsupported_items:
        if callable(ack_fn):
            ack_ok = ack_fn(test_result, "system/settings/list", unsupported_items)
        else:
            msg = f"[INFO] system/settings/list ({version}) claimed unsupported: {unsupported_items}"
            LOGGER.info(msg)
            if getattr(test_result, "logs", None) is not None:
                test_result.logs.append(msg)
    return lat_ok and ack_ok

def start_log_collection(test_result, durationInMs=0, expectedLatencyMs=0):
    try:
        dab_response_validator.validate_start_log_collection_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def stop_log_collection(test_result, durationInMs=0, expectedLatencyMs=0):
    try:
        dab_response_validator.validate_stop_log_collection_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)


def power_mode_get(test_result, durationInMs=0, expectedLatencyMs=0):
    try:
        dab_response_validator.validate_power_mode_get_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def power_mode_set(test_result, durationInMs=0, expectedLatencyMs=0):
    """Validate SetPowerModeResponse schema and verify the requested powerMode is returned."""
    try:
        dab_response_validator.validate_power_mode_set_response_schema(test_result.response)
    except Exception as error:
        _log_validation_error(test_result, f"[FAILED] system/power-mode/set schema error: {_schema_err(error)}")
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    try:
        req = jsons.loads(test_result.request) if isinstance(test_result.request, str) else test_result.request
        if isinstance(req, dict) and "powerMode" in req and response.get("powerMode") != req["powerMode"]:
            _log_validation_error(test_result, f"[FAILED] system/power-mode/set expected powerMode '{req['powerMode']}', got '{response.get('powerMode')}'.")
            return False
    except Exception:
        pass
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)
