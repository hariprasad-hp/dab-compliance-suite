# DAB memory sampler

This is a small, standalone Python sample for DAB devices. It uses the local `mosquitto_pub` and `mosquitto_sub` executables directly; it does not use the main test runner or the Python MQTT library.

It performs this sequence:

1. `applications/list` — find the actual installed DAB app ID.
2. `applications/launch` — launch Netflix or Prime Video.
3. `applications/get-state` — require `FOREGROUND` before sampling.
4. Subscribe to `app-telemetry/metrics/<appId>`.
5. `app-telemetry/start` — request telemetry.
6. Collect raw metric publications for a defined window.
7. `app-telemetry/stop` — always stop telemetry.

## Run

```bash
python3 dab_memory_sample.py \
  --broker 127.0.0.1 \
  --device-id adt-4-ip \
  --app-id Netflix \
  --interval-ms 1000 \
  --sample-seconds 15 \
  --output netflix_memory_sample.json
```

For Prime Video, use `--app-id PrimeVideo`. The script matches app IDs without case sensitivity, then uses the ID returned by `applications/list` for the MQTT telemetry topic.

## Output

The JSON output retains:

- application list, launch result, and application state;
- start/stop telemetry responses;
- every raw MQTT telemetry publication;
- metric records that match the DAB object shape;
- formatting issues that prevent a publication from being treated as a valid DAB metric.

## What memory information it can collect

The DAB spec defines `memory` as an optional numeric value in kilobytes. The sample preserves it exactly as published.

It does **not** claim that `memory` is RSS or PSS. DAB does not expose process IDs, `/proc/<pid>/smaps_rollup`, `/proc/<pid>/status`, or vendor GPU memory. Those measurements require a separate privileged device-side collector or vendor profiling tool.

## Prerequisites

- Python 3 standard library only.
- `mosquitto_pub` and `mosquitto_sub` on `PATH`.
- A DAB device reachable through the MQTT broker.
