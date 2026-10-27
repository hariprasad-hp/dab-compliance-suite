import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
APP_NAME = "dab-compliance-suite"


def _run(cmd):
    print("+", " ".join(str(part) for part in cmd))
    subprocess.check_call([str(part) for part in cmd], cwd=ROOT)


def _copy_docs(bundle_dir):
    shutil.copy2(ROOT / "README.md", bundle_dir / "README.md")
    docs = ROOT / "docs"
    if docs.exists():
        shutil.copytree(docs, bundle_dir / "docs", dirs_exist_ok=True)


def _ensure_test_version():
    path = ROOT / "test_version.txt"
    if not path.exists():
        path.write_text("dev.000000\n", encoding="utf-8")


def _zip_dir(src, dest):
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            arcname = path.relative_to(src.parent)
            info = zipfile.ZipInfo.from_file(path, arcname)
            if path.is_file():
                info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
                with open(path, "rb") as f:
                    zf.writestr(info, f.read())
            else:
                zf.writestr(info, b"")


def main():
    artifact_name = os.environ["BINARY_ARTIFACT_NAME"]
    exe_name = f"{APP_NAME}.exe" if sys.platform.startswith("win") else APP_NAME
    add_data_sep = os.pathsep
    _ensure_test_version()

    _run([
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        APP_NAME,
        "--contents-directory",
        ".",
        "--copy-metadata",
        "readchar",
        "--add-data",
        f"valid_dab_topics.json{add_data_sep}.",
        "--add-data",
        f"test_version.txt{add_data_sep}.",
        "--add-data",
        f"config/apps/unsupported_format_app.txt{add_data_sep}config/apps",
        "--add-data",
        f"test_result/README{add_data_sep}test_result",
        "main.py",
    ])

    bundle_dir = DIST / APP_NAME
    built_exe = bundle_dir / exe_name
    if not built_exe.exists():
        raise FileNotFoundError(built_exe)

    _copy_docs(bundle_dir)
    _zip_dir(bundle_dir, ROOT / artifact_name)


if __name__ == "__main__":
    main()
