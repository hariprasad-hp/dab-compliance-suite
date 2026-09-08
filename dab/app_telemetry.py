from schema import dab_response_validator
from time import sleep
from dab_tester import Default_Validations
import jsons
import math


def validate_metric_messages(messages, require_cpu=False):
    """Validate DAB 2.0 telemetry notification payloads.

    Telemetry is one JSON object per MQTT publication.  CPU is optional in the
    protocol, so callers opt into requiring it only for a CPU-specific test.
    Returns (is_valid, errors, warnings).
    """
    errors = []
    warnings = []
    cpu_seen = False
    last_timestamp = None

    if not messages:
        return False, ["No telemetry notifications received."], warnings

    for index, message in enumerate(messages, 1):
        if not isinstance(message, dict):
            errors.append(f"message {index}: expected a JSON object, got {type(message).__name__}.")
            continue
        missing = {"timestamp", "metric", "value"} - set(message)
        if missing:
            errors.append(f"message {index}: missing required field(s): {', '.join(sorted(missing))}.")
            continue

        timestamp = message["timestamp"]
        metric = message["metric"]
        value = message["value"]
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
            errors.append(f"message {index}: timestamp must be a non-negative integer UNIX time in ms.")
        elif last_timestamp is not None and timestamp < last_timestamp:
            errors.append(f"message {index}: timestamp moved backwards ({timestamp} < {last_timestamp}).")
        else:
            last_timestamp = timestamp

        if metric not in ("cpu", "memory"):
            errors.append(f"message {index}: metric must be 'cpu' or 'memory', got {metric!r}.")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"message {index}: value must be a finite JSON number.")
            continue
        if value < 0:
            errors.append(f"message {index}: {metric} value must not be negative.")
        if metric == "cpu":
            cpu_seen = True
            if value > 100:
                errors.append(f"message {index}: cpu must be in the range 0..100, got {value}.")

    if require_cpu and not cpu_seen:
        errors.append("No 'cpu' telemetry message was received (CPU is optional in DAB, but required by this CPU test).")
    if cpu_seen and all(m.get("value") == 0 for m in messages if isinstance(m, dict) and m.get("metric") == "cpu"):
        warnings.append("All CPU samples are zero. This is allowed by the specification, but may indicate an implementation issue for a foreground app.")
    return not errors, errors, warnings


def start(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_start_device_telemetry_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    response  = jsons.loads(test_result.response)
    if response['status'] != 200:
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)

def stop(test_result, durationInMs=0,expectedLatencyMs=0):
    try:
        dab_response_validator.validate_stop_device_telemetry_response_schema(test_result.response)
    except Exception as error:
        print("Schema error:", error)
        return False
    sleep(0.1)
    return Default_Validations(test_result, durationInMs, expectedLatencyMs)
