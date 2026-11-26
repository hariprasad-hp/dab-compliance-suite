from schema import dab_response_validator
from time import sleep
from dab_tester import YesNoQuestion, Default_Validations
import config
import dab_tester
import jsons
from util.enforcement_manager import EnforcementManager

def send_audio(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_dab_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(5)
    if type(expectedLatencyMs) == int:
        q_ok = YesNoQuestion(test_result, f"Can you verify the voice command has been initated?")
        lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)
        return q_ok and lat_ok
    else:
        return YesNoQuestion(test_result, expectedLatencyMs)

def send_text(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_dab_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(5)
    if type(expectedLatencyMs) == int:
        q_ok = YesNoQuestion(test_result, f"Can you verify the voice command ${test_result.request} has been initated?")
        lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)
        return q_ok and lat_ok
    else:
        return YesNoQuestion(test_result, expectedLatencyMs)

def list(test_result, durationInMs=0,expectedLatencyMs=0):
    """Validate voice/list schema, record latency, and prompt acknowledgment for unsupported/disabled voice systems."""
    raw_vs = jsons.loads(test_result.response).get("voiceSystems") if isinstance(test_result.response, str) else None
    if isinstance(raw_vs, type([])):
        for vs in raw_vs:
            nm = vs.get("name") if isinstance(vs, dict) else None
            if not isinstance(nm, str) or not nm or any(ch.isspace() for ch in nm):
                if getattr(test_result, "logs", None) is not None:
                    test_result.logs.append(f"[FAILED] Invalid voiceSystem name (spaces not supported): {nm!r}")
                return False
    try:
        dab_response_validator.validate_list_voice_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    voice_systems = response.get('voiceSystems') or []
    EnforcementManager().set_supported_voice_assistants(voice_systems)
    sleep(0.1)
    lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)

    unsupported_voice = []
    if not voice_systems:
        unsupported_voice.append("all voice systems (voiceSystems=[])")
    else:
        names = []
        for vs in voice_systems:
            if isinstance(vs, dict):
                nm = vs.get("name", "unknown")
                names.append(nm)
                if vs.get("enabled") is False:
                    unsupported_voice.append(f"{nm} (enabled=false)")
        target_va = getattr(config, "va", None)
        if target_va and target_va not in names:
            unsupported_voice.append(f"{target_va} (not listed)")

    ack_ok = True
    if unsupported_voice:
        ack_fn = getattr(dab_tester, "AcknowledgeUnsupported", None)
        if callable(ack_fn):
            ack_ok = ack_fn(test_result, "voice/list", unsupported_voice)
        elif getattr(test_result, "logs", None) is not None:
            test_result.logs.append(f"[INFO] voice/list unsupported/disabled voice systems: {unsupported_voice}")
    return lat_ok and ack_ok

def set(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_set_voice_system_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)
