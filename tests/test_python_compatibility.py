import importlib
import py_compile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_FILES = [
    REPO_ROOT / "main.py",
    REPO_ROOT / "dab_tester.py",
    REPO_ROOT / "dab_checker.py",
    REPO_ROOT / "util" / "config_loader.py",
    REPO_ROOT / "util" / "runtime_api_server.py",
]
MODULE_IMPORTS = [
    "main",
    "dab_tester",
    "dab_checker",
    "util.config_loader",
    "util.runtime_api_server",
]


class PythonCompatibilityTests(unittest.TestCase):
    def test_python_compatible_files_compile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for file_path in MODULE_FILES:
                with self.subTest(file=str(file_path.relative_to(REPO_ROOT))):
                    py_compile.compile(
                        str(file_path),
                        cfile=str(Path(tmpdir) / (file_path.name + "c")),
                        doraise=True,
                    )

    def test_python_compatible_modules_import(self):
        for module_name in MODULE_IMPORTS:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)
