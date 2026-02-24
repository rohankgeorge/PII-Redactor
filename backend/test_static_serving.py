"""Tests for Milestone 4: static frontend serving and build script existence."""

import importlib
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).parent
ROOT_DIR = BACKEND_DIR.parent


@pytest.fixture()
def frontend_build_dir(tmp_path):
    """Create a temporary frontend_build directory with a minimal index.html."""
    build_dir = BACKEND_DIR / "frontend_build"
    already_existed = build_dir.exists()
    if not already_existed:
        build_dir.mkdir()
    index_html = build_dir / "index.html"
    wrote_index = not index_html.exists()
    if wrote_index:
        index_html.write_text(
            "<html><body><h1>PII Redactor</h1></body></html>",
            encoding="utf-8",
        )
    yield build_dir
    # Cleanup
    if wrote_index and index_html.exists():
        index_html.unlink()
    if not already_existed and build_dir.exists():
        shutil.rmtree(build_dir)


def _reload_server_module():
    """Force re-import of server module so static mount is re-evaluated."""
    # Remove cached module
    for mod_name in list(sys.modules):
        if mod_name == "server":
            del sys.modules[mod_name]
    import server as srv
    return srv


def test_api_health_endpoint():
    """Backend health endpoint responds regardless of frontend_build."""
    import server
    client = TestClient(server.app)
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_static_serving_with_frontend_build(frontend_build_dir):
    """When frontend_build/ exists, the root serves the index.html."""
    srv = _reload_server_module()
    client = TestClient(srv.app)

    response = client.get("/")
    assert response.status_code == 200
    assert "PII Redactor" in response.text


def test_installer_directory_structure():
    """Verify installer directory has all required files."""
    installer_dir = ROOT_DIR / "installer"
    assert installer_dir.is_dir(), "installer/ directory must exist"

    expected_files = [
        "build_installer.py",
        "build_backend.py",
        "pyinstaller.spec",
        "README_BUILD.md",
        "electron-app/main.js",
        "electron-app/preload.js",
        "electron-app/package.json",
    ]

    for rel_path in expected_files:
        full_path = installer_dir / rel_path
        assert full_path.is_file(), f"Missing installer file: {rel_path}"


def test_build_backend_script_importable():
    """build_backend.py can be imported without errors."""
    build_script = ROOT_DIR / "installer" / "build_backend.py"
    assert build_script.is_file()

    import importlib.util
    spec = importlib.util.spec_from_file_location("build_backend", str(build_script))
    mod = importlib.util.module_from_spec(spec)
    # Just check it loads — don't execute build()
    spec.loader.exec_module(mod)
    assert hasattr(mod, "build")


def test_pyinstaller_spec_is_valid_python():
    """pyinstaller.spec is valid Python syntax."""
    spec_file = ROOT_DIR / "installer" / "pyinstaller.spec"
    assert spec_file.is_file()
    source = spec_file.read_text(encoding="utf-8")
    # Should compile without syntax errors
    compile(source, str(spec_file), "exec")


def test_electron_package_json_valid():
    """Electron package.json has required fields."""
    import json
    pkg_file = ROOT_DIR / "installer" / "electron-app" / "package.json"
    assert pkg_file.is_file()
    pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
    assert pkg.get("name") == "pii-redactor"
    assert "main" in pkg
    assert "build" in pkg
    assert "win" in pkg["build"]
    assert "mac" in pkg["build"]
