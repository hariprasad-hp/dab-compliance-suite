import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_REPO = "device-automation-bus/dab-compliance-suite"


def platform_id():
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    if system == "darwin":
        return f"macos-{arch}"
    if system == "windows":
        return "windows-x64"
    if system == "linux":
        return f"linux-{arch}"
    raise RuntimeError(f"Unsupported update platform: {platform.system()} {platform.machine()}")


def current_version():
    try:
        with open("test_version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "dev.000000"


def default_install_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _read_json(path_or_url):
    if path_or_url.startswith(("http://", "https://")):
        with urllib.request.urlopen(path_or_url, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    with open(path_or_url, "r", encoding="utf-8") as f:
        return json.load(f)


def _github_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "dab-compliance-suite-updater",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _download(url, dest_dir):
    target = Path(dest_dir) / Path(url.split("?", 1)[0]).name
    with urllib.request.urlopen(url, timeout=300) as response:
        with open(target, "wb") as f:
            shutil.copyfileobj(response, f)
    return target


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_versions(manifest):
    versions = manifest.get("versions", {})
    if isinstance(versions, dict):
        return versions
    if isinstance(versions, list):
        return {
            str(item.get("version")): item
            for item in versions
            if isinstance(item, dict) and item.get("version")
        }
    return {}


def resolve_update(version="latest", manifest_url=None):
    if not manifest_url:
        return _resolve_github_release(version=version)

    manifest = _read_json(manifest_url)
    versions = _manifest_versions(manifest)
    wanted = manifest.get("latest") if version in (None, "", "latest") else version
    if not wanted or wanted not in versions:
        available = ", ".join(sorted(versions.keys())) or "<none>"
        raise RuntimeError(f"Version '{version}' not found. Available: {available}")
    entry = versions[wanted]
    if not isinstance(entry, dict):
        raise RuntimeError(f"Version '{wanted}' is malformed in manifest.")
    if entry.get("url"):
        return wanted, entry
    assets = entry.get("assets")
    if isinstance(assets, dict):
        platform_entry = assets.get(platform_id())
        if isinstance(platform_entry, dict) and platform_entry.get("url"):
            return wanted, platform_entry
    raise RuntimeError(f"Version '{wanted}' has no update URL for {platform_id()}.")


def _asset_entry(release):
    wanted = f"dab-compliance-suite-{platform_id()}.zip"
    for asset in release.get("assets", []):
        if asset.get("name") == wanted:
            return {
                "url": asset.get("browser_download_url"),
                "sha256": None,
            }
    raise RuntimeError(f"Release has no asset named {wanted}.")


def _resolve_github_release(version="latest"):
    repo = os.environ.get("DAB_UPDATE_REPO", DEFAULT_REPO)
    base = f"https://api.github.com/repos/{repo}/releases"
    if version in (None, "", "latest"):
        release = _github_json(f"{base}/latest")
    else:
        tag = str(version)
        if not tag.startswith("test-"):
            tag = f"test-{tag}"
        release = _github_json(f"{base}/tags/{tag}")
    tag_name = str(release.get("tag_name", "")).removeprefix("test-")
    return tag_name, _asset_entry(release)


def _payload_root(extract_dir):
    entries = [p for p in Path(extract_dir).iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return Path(extract_dir)


def _replace_tree(src, dest):
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
        os.close(fd)
        try:
            shutil.copy2(path, tmp_name)
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


def _mark_executables(install_dir):
    for name in ("dab-compliance-suite", "dab-compliance-suite.exe"):
        path = Path(install_dir) / name
        if path.exists():
            path.chmod(path.stat().st_mode | 0o111)


def install_update(update_path, install_dir=None, expected_sha256=None):
    update_path = Path(update_path).resolve()
    install_dir = Path(install_dir).resolve() if install_dir else default_install_dir()
    if not update_path.exists():
        raise FileNotFoundError(update_path)
    if expected_sha256 and _sha256(update_path).lower() != expected_sha256.lower():
        raise RuntimeError("Downloaded update checksum did not match manifest.")

    with tempfile.TemporaryDirectory(prefix="dab-update-") as tmp:
        if zipfile.is_zipfile(update_path):
            with zipfile.ZipFile(update_path, "r") as zf:
                zf.extractall(tmp)
            payload = _payload_root(tmp)
            _replace_tree(payload, install_dir)
            _mark_executables(install_dir)
        else:
            target = install_dir / update_path.name
            fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(install_dir))
            os.close(fd)
            try:
                shutil.copy2(update_path, tmp_name)
                os.replace(tmp_name, target)
                target.chmod(target.stat().st_mode | 0o111)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)

    return install_dir


def update_from_source(source, install_dir=None, sha256=None):
    with tempfile.TemporaryDirectory(prefix="dab-download-") as tmp:
        if source.startswith(("http://", "https://")):
            source_path = _download(source, tmp)
        else:
            source_path = Path(source)
        return install_update(source_path, install_dir=install_dir, expected_sha256=sha256)


def update_from_manifest(version="latest", manifest_url=None, install_dir=None):
    resolved_version, entry = resolve_update(version=version, manifest_url=manifest_url)
    install_path = update_from_source(
        entry["url"],
        install_dir=install_dir,
        sha256=entry.get("sha256"),
    )
    return resolved_version, install_path
