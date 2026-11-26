from schema import dab_response_validator
from time import sleep
from dab_tester import YesNoQuestion, Default_Validations
import dab_tester
from logger import LOGGER
from util.enforcement_manager import EnforcementManager
import json
import re

COMMON_KEY_CODES = {
    "KEY_POWER", "KEY_HOME", "KEY_VOLUME_UP", "KEY_VOLUME_DOWN", "KEY_MUTE",
    "KEY_CHANNEL_UP", "KEY_CHANNEL_DOWN", "KEY_MENU", "KEY_EXIT", "KEY_INFO",
    "KEY_GUIDE", "KEY_CAPTIONS", "KEY_UP", "KEY_PAGE_UP", "KEY_PAGE_DOWN",
    "KEY_RIGHT", "KEY_DOWN", "KEY_LEFT", "KEY_ENTER", "KEY_BACK",
    "KEY_PLAY", "KEY_PLAY_PAUSE", "KEY_PAUSE", "KEY_RECORD", "KEY_STOP",
    "KEY_REWIND", "KEY_FAST_FORWARD", "KEY_SKIP_REWIND", "KEY_SKIP_FAST_FORWARD",
    "KEY_0", "KEY_1", "KEY_2", "KEY_3", "KEY_4", "KEY_5", "KEY_6", "KEY_7", "KEY_8", "KEY_9",
    "KEY_RED", "KEY_GREEN", "KEY_YELLOW", "KEY_BLUE",
}

class KeyList:
    key_list = []

def key_press(test_result, durationInMs=0, expectedLatencyMs=None):
    try:
        dab_response_validator.validate_dab_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    request = json.loads(test_result.request)
    response  = json.loads(test_result.response)
    # No list available, assuming everything is required.
    if len(KeyList.key_list) <=0:
        if response['status'] != 200:
            return False
    else:
        if request['keyCode'] in KeyList.key_list:
            if response['status'] != 200:
                return False
        else:
            if response['status'] != 501:
                return False
    sleep(1)

    # Remove YesNoQuestion → directly validate
    if isinstance(expectedLatencyMs, int):
        return Default_Validations(test_result, durationInMs, expectedLatencyMs)
    else:
        return True
    
def long_key_press(test_result, durationInMs=0, expectedLatencyMs=None):
    try:
        dab_response_validator.validate_dab_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    request = json.loads(test_result.request)
    response  = json.loads(test_result.response)
    # No list available, assuming everything is required.
    if len(KeyList.key_list) <=0:
        if response['status'] != 200:
            return False
    else:
        if request['keyCode'] in KeyList.key_list:
            if response['status'] != 200:
                return False
        else:
            if response['status'] != 501:
                return False

    sleep(1)
    # Remove YesNoQuestion → directly validate
    if isinstance(expectedLatencyMs, int):
        return Default_Validations(test_result, durationInMs, expectedLatencyMs)
    else:
        return True

def list(test_result, durationInMs=0, expectedLatencyMs=0):
    """Validate input/key/list entries, warn on 3P key names, and acknowledge missing standard keys."""
    raw_keys = json.loads(test_result.response).get("keyCodes") if isinstance(test_result.response, str) else None
    if isinstance(raw_keys, type([])):
        for k in raw_keys:
            if not isinstance(k, str) or not k or any(ch.isspace() for ch in k):
                if getattr(test_result, "logs", None) is not None:
                    test_result.logs.append(f"[FAILED] Invalid keyCode (whitespace/empty not supported): {k!r}")
                return False
    try:
        dab_response_validator.validate_key_list_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = json.loads(test_result.response)
    if response['status'] != 200:
        return False
    if len(response['keyCodes']) <= 0:
        return False
    for key in response['keyCodes']:
        if not isinstance(key, str) or not (1 <= len(key) <= 64):
            if getattr(test_result, "logs", None) is not None:
                test_result.logs.append(f"[FAILED] Invalid keyCode entry in input/key/list: {key!r}")
            return False
        if key not in COMMON_KEY_CODES and not re.match(r"^KEY_CUSTOM_[A-Za-z0-9_]+$", key):
            warn_msg = f"[WARN] Non-standard partner keyCode in input/key/list: {key!r} (recommended prefix: KEY_CUSTOM_*)."
            LOGGER.warn(warn_msg)
            if getattr(test_result, "logs", None) is not None:
                test_result.logs.append(warn_msg)
    KeyList.key_list = response['keyCodes']
    EnforcementManager().add_supported_keys(KeyList.key_list)
    sleep(0.1)
    lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)

    missing_keys = sorted(COMMON_KEY_CODES - set(response['keyCodes']))
    ack_ok = True
    if missing_keys:
        ack_fn = getattr(dab_tester, "AcknowledgeUnsupported", None)
        if callable(ack_fn):
            ack_ok = ack_fn(test_result, "input/key/list", missing_keys)
        elif getattr(test_result, "logs", None) is not None:
            test_result.logs.append(f"[INFO] input/key/list omitted standard keys: {missing_keys}")
    return lat_ok and ack_ok
