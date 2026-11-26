from schema import dab_response_validator
from time import sleep
from dab_tester import YesNoQuestion, Default_Validations
import dab_tester
import jsons
from util.enforcement_manager import EnforcementManager

DAB_20_OPERATIONS = ['applications/list', 'applications/launch', 'applications/launch-with-content', 'applications/get-state', 'applications/exit', 'device/info', 'system/restart', 'system/settings/list', 'system/settings/get', 'system/settings/set', 'input/key/list', 'input/key-press', 'input/long-key-press', 'output/image', 'device-telemetry/start', 'device-telemetry/stop', 'app-telemetry/start', 'app-telemetry/stop', 'health-check/get', 'voice/list', 'voice/set', 'voice/send-audio', 'voice/send-text', 'version']
DAB_21_OPERATIONS = DAB_20_OPERATIONS + ['applications/install', 'applications/uninstall', 'applications/clear-data', 'applications/install-from-app-store', 'system/logs/start-collection', 'system/logs/stop-collection', 'system/power-mode/get', 'system/power-mode/set', 'system/factory-reset', 'system/network-reset', 'content/search', 'content/recommendations', 'content/open']

def list(test_result, durationInMs=0,expectedLatencyMs=0):
    """Cache supported operations, prompt acknowledgment for omitted operations, and verify DAB §5.1 rules."""
    raw_ops = jsons.loads(test_result.response).get("operations") if isinstance(test_result.response, str) else None
    if isinstance(raw_ops, type([])):
        bad_ws = [op for op in raw_ops if isinstance(op, str) and (not op or any(ch.isspace() for ch in op))]
        if bad_ws:
            if getattr(test_result, "logs", None) is not None:
                test_result.logs.append(f"[FAILED] operations/list contains whitespace in operation name: {bad_ws[0]!r}")
            return False
    try:
        dab_response_validator.validate_list_supported_operation_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        if getattr(test_result, "logs", None) is not None:
            test_result.logs.append(f"[FAILED] Schema error: {error}")
        return False
    response = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    ops = response.get('operations') or []
    for operation in ops:
        if isinstance(operation, str) and operation.strip() and not operation.startswith("dab/"):
            EnforcementManager().add_supported_operation(operation.strip())

    sleep(0.1)
    lat_ok = Default_Validations(test_result, durationInMs, expectedLatencyMs)

    if not ops:
        if getattr(test_result, "logs", None) is not None:
            test_result.logs.append("[FAILED] operations/list returned an empty operations array.")
        return False

    version = getattr(dab_tester, "DAB_VERSION", None) or "2.0"
    expected_ops = DAB_21_OPERATIONS if version >= "2.1" else DAB_20_OPERATIONS
    missing_ops = [op for op in expected_ops if op not in ops]
    ack_ok = True
    if missing_ops:
        ack_fn = getattr(dab_tester, "AcknowledgeUnsupported", None)
        if callable(ack_fn):
            ack_ok = ack_fn(test_result, "operations/list", missing_ops)
        elif getattr(test_result, "logs", None) is not None:
            test_result.logs.append(f"[INFO] operations/list omitted unsupported operations: {missing_ops}")

    if "operations/list" in ops:
        if getattr(test_result, "logs", None) is not None:
            test_result.logs.append("[FAILED] operations/list must not include 'operations/list' itself per DAB spec.")
        return False
    for operation in ops:
        if not isinstance(operation, str) or not operation.strip() or any(ch.isspace() for ch in operation) or operation.startswith("dab/"):
            if getattr(test_result, "logs", None) is not None:
                test_result.logs.append(f"[FAILED] Invalid operation topic name in operations/list: {operation!r}")
            return False
    return lat_ok and ack_ok
