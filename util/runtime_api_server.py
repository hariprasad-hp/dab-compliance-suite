"""
Temporary HTTP bridge for applications/install tests.

This module serves local app artifacts over HTTP so DAB devices on the
same network can fetch them during install tests. It can also accept an
artifact upload when the expected file is missing from config/apps/.

The bridge is started lazily by the payload builder and is stopped by the
test runner after the install-focused test finishes.
"""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from logger import LOGGER
from util.config_loader import DEFAULT_CONFIG_DIR, make_app_id_list

RUNTIME_INSTALL_BRIDGE_HOST = "0.0.0.0"
RUNTIME_INSTALL_BRIDGE_PORT = 8765
_ACTIVE_HANDLE = None
_ACTIVE_LOCK = threading.Lock()
_UPLOAD_EVENTS = {}
_UPLOAD_EVENTS_LOCK = threading.Lock()


@dataclass
class RuntimeApiServerHandle:
    """Handle for the currently running temporary install bridge."""

    host: str
    port: int
    public_host: str
    server: object
    thread: threading.Thread

    def stop(self) -> None:
        """Request shutdown and wait briefly for the server thread."""
        self.server.should_exit = True
        self.thread.join(timeout=2)


def _artifact_path(app_id: str, config_dir: str = DEFAULT_CONFIG_DIR) -> Optional[Path]:
    """Return the first matching artifact for an app ID from config/apps/."""
    root = Path(config_dir)
    if not root.exists():
        return None

    target = app_id.lower()
    for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not entry.is_file():
            continue
        name = entry.name.lower()
        if name == target or name.startswith(target + "."):
            return entry.resolve()
    return None


def _pick_available_port(host: str, preferred_port: int, attempts: int = 20) -> int:
    """Pick the first bindable port, starting at the preferred port."""
    preferred = int(preferred_port)
    last_error = None

    for port in range(preferred, preferred + max(attempts, 1)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((host, port))
            return port
        except OSError as exc:
            last_error = exc
        finally:
            sock.close()

    raise RuntimeError(
        f"No free runtime install bridge port found in range {preferred}-{preferred + max(attempts, 1) - 1}: {last_error}"
    )


def _resolve_public_host(bind_host: str) -> str:
    """Best-effort host/IP to advertise to a DAB device."""
    env_host = ""
    try:
        import os

        env_host = (os.getenv("DAB_INSTALL_HOST") or "").strip()
    except Exception:
        env_host = ""

    if env_host:
        return env_host

    if bind_host not in {"0.0.0.0", "::"}:
        return bind_host

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            host = sock.getsockname()[0]
            if host:
                return host
        finally:
            sock.close()
    except Exception:
        pass

    try:
        host = socket.gethostbyname(socket.gethostname())
        if host:
            return host
    except Exception:
        pass

    return "127.0.0.1"


def _runtime_install_wait_timeout() -> Optional[float]:
    """Read an optional upload wait timeout from the environment."""
    try:
        import os

        raw = (os.getenv("DAB_INSTALL_WAIT_TIMEOUT_SEC") or "").strip()
    except Exception:
        raw = ""

    if not raw:
        return None

    try:
        timeout = float(raw)
    except Exception:
        LOGGER.warn(f"[RUNTIME INSTALL] Ignoring invalid DAB_INSTALL_WAIT_TIMEOUT_SEC value: {raw}")
        return None

    return timeout if timeout > 0 else None


def create_runtime_install_app(
    config_dir: str = DEFAULT_CONFIG_DIR,
    expected_app_id: Optional[str] = None,
    upload_event: Optional[threading.Event] = None,
):
    """Create the FastAPI app used by the temporary install bridge."""
    try:
        from fastapi import FastAPI, File, HTTPException, UploadFile
    except Exception as exc:
        raise RuntimeError(f"FastAPI runtime install bridge is unavailable: {exc}") from exc

    apps_dir = Path(config_dir)
    allowed_ids = make_app_id_list()
    lock = threading.Lock()
    app = FastAPI(
        title="DAB Runtime Install Bridge",
        version="1.0",
        description="Temporary upload bridge for applications/install payload composition.",
    )

    def resolve_app_id(raw_app_id: str) -> str:
        for allowed in allowed_ids:
            if allowed.lower() == (raw_app_id or "").strip().lower():
                return allowed
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Unsupported appId '{raw_app_id}'.",
                "allowedAppIds": allowed_ids,
            },
        )

    def remove_existing_artifacts(app_id: str) -> None:
        if not apps_dir.exists():
            return
        target = app_id.lower()
        for entry in list(apps_dir.iterdir()):
            if not entry.is_file():
                continue
            name = entry.name.lower()
            if name == target or name.startswith(target + "."):
                entry.unlink()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/runtime/install/state")
    def state():
        artifacts = {}
        for app_id in allowed_ids:
            artifact = _artifact_path(app_id, config_dir=config_dir)
            artifacts[app_id] = str(artifact) if artifact else None
        return {
            "allowedAppIds": allowed_ids,
            "artifacts": artifacts,
            "appsDir": str(apps_dir.resolve()),
        }

    @app.get("/runtime/install/files/{artifact_name}")
    def fetch_runtime_artifact(artifact_name: str):
        artifact = (apps_dir / artifact_name).resolve()
        try:
            artifact.relative_to(apps_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid artifact path")
        if not artifact.is_file():
            raise HTTPException(status_code=404, detail=f"No artifact found for '{artifact_name}'")

        from fastapi.responses import FileResponse

        return FileResponse(str(artifact), filename=artifact.name)

    @app.post("/runtime/install/artifacts/{app_id}")
    def upload_runtime_artifact(app_id: str, file: UploadFile = File(...)):
        resolved_app_id = resolve_app_id(app_id)
        if not (file.filename or "").strip():
            raise HTTPException(status_code=400, detail="Uploaded file must include a filename")

        suffix = Path(file.filename).suffix or ".bin"
        destination = apps_dir / f"{resolved_app_id}{suffix}"

        with lock:
            apps_dir.mkdir(parents=True, exist_ok=True)
            remove_existing_artifacts(resolved_app_id)
            with destination.open("wb") as file_obj:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    file_obj.write(chunk)

        if upload_event is not None and (expected_app_id is None or resolved_app_id == expected_app_id):
            upload_event.set()
        with _UPLOAD_EVENTS_LOCK:
            event = _UPLOAD_EVENTS.get(resolved_app_id)
        if event is not None:
            event.set()

        return {
            "message": f"Stored install artifact for '{resolved_app_id}'.",
            "artifact": {
                "appId": resolved_app_id,
                "path": str(destination.resolve()),
                "filename": destination.name,
                "contentType": file.content_type or "application/octet-stream",
            },
        }

    return app


def start_runtime_install_bridge(
    host: str = RUNTIME_INSTALL_BRIDGE_HOST,
    preferred_port: int = RUNTIME_INSTALL_BRIDGE_PORT,
    config_dir: str = DEFAULT_CONFIG_DIR,
    expected_app_id: Optional[str] = None,
    upload_event: Optional[threading.Event] = None,
) -> RuntimeApiServerHandle:
    """Start the shared runtime install bridge if it is not already running."""
    global _ACTIVE_HANDLE

    try:
        import uvicorn
    except Exception as exc:
        raise RuntimeError(f"uvicorn is required for the runtime install bridge: {exc}") from exc

    with _ACTIVE_LOCK:
        if _ACTIVE_HANDLE is not None:
            return _ACTIVE_HANDLE

        port = _pick_available_port(host=host, preferred_port=preferred_port)
        if port != int(preferred_port):
            LOGGER.warn(
                f"[RUNTIME INSTALL] Port {preferred_port} is busy. Falling forward to available port {port}."
            )

        app = create_runtime_install_app(
            config_dir=config_dir,
            expected_app_id=expected_app_id,
            upload_event=upload_event,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="warning",
            )
        )
        thread = threading.Thread(target=server.run, name="dab-runtime-install-bridge", daemon=True)
        thread.start()
        public_host = _resolve_public_host(host)
        if public_host == "127.0.0.1" and host in {"0.0.0.0", "::"}:
            LOGGER.warn(
                "[RUNTIME INSTALL] Could not confidently detect a LAN IP. "
                "Set DAB_INSTALL_HOST to the host machine IP if the device is on another machine."
            )

        LOGGER.result(f"[RUNTIME INSTALL] Temporary bridge listening on {host}:{port}")
        LOGGER.result(f"[RUNTIME INSTALL] Artifact host for devices: http://{public_host}:{port}")
        LOGGER.result("[RUNTIME INSTALL] Upload endpoint: /runtime/install/artifacts/{appId}")

        _ACTIVE_HANDLE = RuntimeApiServerHandle(
            host=host,
            port=port,
            public_host=public_host,
            server=server,
            thread=thread,
        )
        return _ACTIVE_HANDLE


def stop_runtime_install_bridge() -> None:
    """Stop the shared runtime install bridge, if one is running."""
    global _ACTIVE_HANDLE

    with _ACTIVE_LOCK:
        handle = _ACTIVE_HANDLE
        _ACTIVE_HANDLE = None

    if handle is not None:
        handle.stop()
        LOGGER.info("[RUNTIME INSTALL] Temporary bridge stopped.")


def wait_for_runtime_install_artifact(
    app_id: str,
    config_dir: str = DEFAULT_CONFIG_DIR,
) -> Optional[Path]:
    """
    For DAB 2.1+ local install flows, start a temporary upload bridge only when the
    expected artifact is missing, wait for a runtime upload signal, then shut it down.
    """
    existing = _artifact_path(app_id, config_dir=config_dir)
    if existing:
        return existing

    handle = None
    upload_event = threading.Event()
    try:
        with _UPLOAD_EVENTS_LOCK:
            _UPLOAD_EVENTS[app_id] = upload_event
        handle = start_runtime_install_bridge(
            config_dir=config_dir,
            expected_app_id=app_id,
            upload_event=upload_event,
        )
        LOGGER.warn(
            f"[RUNTIME INSTALL] Waiting for '{app_id}' to be uploaded into {config_dir}."
        )
        timeout = _runtime_install_wait_timeout()
        if not upload_event.wait(timeout=timeout):
            if timeout is not None:
                LOGGER.warn(
                    f"[RUNTIME INSTALL] Timed out waiting {timeout:g}s for '{app_id}' upload."
                )
                stop_runtime_install_bridge()
            return None
        artifact = _artifact_path(app_id, config_dir=config_dir)
        if artifact:
            LOGGER.ok(f"[RUNTIME INSTALL] Received install artifact for '{app_id}': {artifact}")
            return artifact
    except Exception as exc:
        LOGGER.warn(f"[RUNTIME INSTALL] Temporary bridge could not start: {exc}")
        return None
    finally:
        with _UPLOAD_EVENTS_LOCK:
            _UPLOAD_EVENTS.pop(app_id, None)

    return None


def get_runtime_install_url(
    app_id: str,
    config_dir: str = DEFAULT_CONFIG_DIR,
) -> str:
    """Build the HTTP URL a device should use to fetch an app artifact."""
    handle = start_runtime_install_bridge(config_dir=config_dir)
    artifact = _artifact_path(app_id, config_dir=config_dir)
    if not artifact:
        raise FileNotFoundError(f"No artifact found for '{app_id}' in '{config_dir}'")
    return f"http://{handle.public_host}:{handle.port}/runtime/install/files/{artifact.name}"
