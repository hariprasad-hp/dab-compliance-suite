#!/usr/bin/env python3
"""Small DAB app-memory sampler using mosquitto_pub and mosquitto_sub.

It intentionally keeps raw notifications.  DAB defines only a generic numeric
``memory`` metric; this tool does not relabel it as RSS or PSS.
"""

import argparse
import json
import subprocess
import sys
import time
import uuid


class DabMosquittoClient:
    def __init__(self, broker, port):
        self.broker = broker
        self.port = str(port)

    def _base(self, program):
        return [program, "-h", self.broker, "-p", self.port, "-V", "mqttv5"]

    def request(self, device_id, operation, payload, timeout=10):
        """Send one DAB request and return its JSON response."""
        response_topic = "dab/_response/memory-sample/" + uuid.uuid4().hex
        subscriber = subprocess.Popen(
            self._base("mosquitto_sub") + ["-t", response_topic, "-C", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(0.15)  # ensure the response subscription exists first
            publisher = subprocess.run(
                self._base("mosquitto_pub")
                + [
                    "-t", f"dab/{device_id}/{operation}",
                    "-m", json.dumps(payload),
                    "-D", "publish", "response-topic", response_topic,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if publisher.returncode:
                raise RuntimeError(publisher.stderr.strip() or "mosquitto_pub failed")
            output, error = subscriber.communicate(timeout=timeout)
            if subscriber.returncode not in (0, None):
                raise RuntimeError(error.strip() or "mosquitto_sub failed")
            return json.loads(output)
        except subprocess.TimeoutExpired as error:
            subscriber.kill()
            subscriber.communicate()
            raise RuntimeError(f"Timed out waiting for {operation}") from error
        finally:
            if subscriber.poll() is None:
                subscriber.terminate()
                subscriber.communicate()

    def capture(self, device_id, operation, seconds):
        """Capture raw notification payloads from one DAB topic for *seconds*."""
        topic = f"dab/{device_id}/{operation}"
        subscriber = subprocess.Popen(
            self._base("mosquitto_sub") + ["-t", topic, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(seconds)
            subscriber.terminate()
            output, error = subscriber.communicate(timeout=3)
        finally:
            if subscriber.poll() is None:
                subscriber.kill()
                subscriber.communicate()

        if error.strip():
            print(f"[mosquitto_sub] {error.strip()}", file=sys.stderr)
        payloads = []
        for line in output.splitlines():
            _topic, separator, payload = line.partition(" ")
            if not separator:
                payload = line
            try:
                payloads.append(json.loads(payload))
            except json.JSONDecodeError:
                payloads.append({"_invalid_json": payload})
        return payloads


def telemetry_summary(payloads):
    """Return raw metric observations and identify DAB schema issues."""
    observations = []
    issues = []
    for publication_no, payload in enumerate(payloads, 1):
        if not isinstance(payload, dict):
            issues.append(f"publication {publication_no}: expected a JSON object, got {type(payload).__name__}")
            continue
        missing = {"timestamp", "metric", "value"} - set(payload)
        if missing:
            issues.append(f"publication {publication_no}: missing {sorted(missing)}")
            continue
        observation = {
            "timestamp": payload["timestamp"],
            "metric": payload["metric"],
            "value": payload["value"],
        }
        observations.append(observation)
        if not isinstance(payload["timestamp"], int) or isinstance(payload["timestamp"], bool):
            issues.append(f"publication {publication_no}: timestamp is not a numeric UNIX-ms value")
        if not isinstance(payload["value"], (int, float)) or isinstance(payload["value"], bool):
            issues.append(f"publication {publication_no}: value is not numeric")
        if payload["metric"] == "cpu" and isinstance(payload["value"], (int, float)) and not 0 <= payload["value"] <= 100:
            issues.append(f"publication {publication_no}: cpu is outside 0..100")
    return observations, issues


def main():
    parser = argparse.ArgumentParser(description="Collect DAB application telemetry with mosquitto commands.")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--app-id", default="Netflix", help="DAB app ID, e.g. Netflix or PrimeVideo")
    parser.add_argument("--interval-ms", type=int, default=1000)
    parser.add_argument("--sample-seconds", type=float, default=10)
    parser.add_argument("--output", default="memory_sample.json")
    args = parser.parse_args()

    dab = DabMosquittoClient(args.broker, args.port)
    apps_response = dab.request(args.device_id, "applications/list", {})
    if apps_response.get("status") != 200:
        raise SystemExit(f"applications/list failed: {apps_response}")
    apps = apps_response.get("applications", [])
    actual_app_id = next(
        (app.get("appId") for app in apps if str(app.get("appId", "")).lower() == args.app_id.lower()),
        None,
    )
    if not actual_app_id:
        available = ", ".join(str(app.get("appId")) for app in apps)
        raise SystemExit(f"{args.app_id!r} is not installed. Available apps: {available}")

    launch_response = dab.request(args.device_id, "applications/launch", {"appId": actual_app_id})
    state_response = dab.request(args.device_id, "applications/get-state", {"appId": actual_app_id})
    result = {
        "device_id": args.device_id,
        "app_id": actual_app_id,
        "applications_list": apps_response,
        "launch_response": launch_response,
        "state_response": state_response,
        "telemetry_topic": f"dab/{args.device_id}/app-telemetry/metrics/{actual_app_id}",
    }

    if launch_response.get("status") != 200 or state_response.get("state") != "FOREGROUND":
        result["note"] = "Telemetry was not started: the app did not reach FOREGROUND."
        with open(args.output, "w", encoding="utf-8") as output_file:
            json.dump(result, output_file, indent=2)
        print(json.dumps(result, indent=2))
        raise SystemExit(2)

    # Subscribe before starting telemetry: some devices publish immediately.
    # capture() runs in a process so start the subscription manually here.
    topic = result["telemetry_topic"]
    subscriber = subprocess.Popen(
        dab._base("mosquitto_sub") + ["-t", topic, "-v"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    start_response = None
    try:
        time.sleep(0.15)
        start_response = dab.request(args.device_id, "app-telemetry/start", {"appId": actual_app_id, "duration": args.interval_ms})
        time.sleep(args.sample_seconds)
    finally:
        stop_response = dab.request(args.device_id, "app-telemetry/stop", {"appId": actual_app_id})
        subscriber.terminate()
        raw_output, raw_error = subscriber.communicate(timeout=3)

    raw_payloads = []
    for line in raw_output.splitlines():
        _topic, separator, payload = line.partition(" ")
        try:
            raw_payloads.append(json.loads(payload if separator else line))
        except json.JSONDecodeError:
            raw_payloads.append({"_invalid_json": payload if separator else line})
    observations, issues = telemetry_summary(raw_payloads)
    result.update({
        "start_response": start_response,
        "stop_response": stop_response,
        "raw_telemetry_publications": raw_payloads,
        "valid_dab_metric_observations": observations,
        "telemetry_format_issues": issues,
        "subscriber_stderr": raw_error.strip(),
        "memory_scope_note": "DAB memory is a generic device-provided KB metric. It is not RSS, PSS, or GPU memory.",
    })
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
