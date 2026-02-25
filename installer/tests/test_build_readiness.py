"""Pre-flight and post-build tests for the PII Redactor installer pipeline.

Pre-flight tests validate that all prerequisites are in place BEFORE
starting the expensive build.  Post-build tests verify the output
artifacts.

Usage:
    # Pre-flight only (fast, run first)
    python -m pytest installer/tests/test_build_readiness.py -v -k "not post_build"

    # Post-build only (after build_installer.py finishes)
    python -m pytest installer/tests/test_build_readiness.py -v -k "post_build"
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
INSTALLER = ROOT / "installer"
ELECTRON_APP = INSTALLER / "electron-app"
DIST = ROOT / "dist"
BACKEND_DIST = ROOT / "backend_dist"


# ── Pre-flight tests ────────────────────────────────────────


class TestPreflight:
    """Tests that must pass before running the build pipeline."""

    def test_python_version_gte_310(self):
        assert sys.version_info >= (3, 10), (
            f"Python >= 3.10 required, got {sys.version}"
        )

    def test_node_available(self):
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Node.js is not installed or not on PATH"
        version_str = result.stdout.strip().lstrip("v")
        major = int(version_str.split(".")[0])
        assert major >= 18, f"Node >= 18 required, got {version_str}"

    def test_pyinstaller_installed(self):
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            pytest.fail("PyInstaller is not installed (pip install pyinstaller)")

    def test_spacy_model_installed(self):
        import spacy.util

        try:
            spacy.util.get_package_path("en_core_web_sm")
        except Exception:
            pytest.fail(
                "spaCy model en_core_web_sm not installed "
                "(python -m spacy download en_core_web_sm)"
            )

    def test_backend_entry_point_exists(self):
        assert (BACKEND / "server.py").is_file(), "backend/server.py not found"

    def test_backend_data_dirs_exist(self):
        assert (BACKEND / "data").is_dir(), "backend/data/ not found"
        assert (BACKEND / "name_data").is_dir(), "backend/name_data/ not found"

    def test_backend_user_lists_exist(self):
        assert (BACKEND / "user_allow_list.txt").is_file(), (
            "backend/user_allow_list.txt not found"
        )
        assert (BACKEND / "user_redact_list.txt").is_file(), (
            "backend/user_redact_list.txt not found"
        )

    def test_frontend_package_json_exists(self):
        assert (FRONTEND / "package.json").is_file(), (
            "frontend/package.json not found"
        )

    def test_electron_nsis_config(self):
        pkg_path = ELECTRON_APP / "package.json"
        assert pkg_path.is_file(), "electron-app/package.json not found"
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        build = pkg.get("build", {})
        nsis = build.get("nsis", {})

        assert nsis.get("oneClick") is False, "nsis.oneClick must be false"
        assert nsis.get("perMachine") is True, "nsis.perMachine must be true"
        assert nsis.get("allowToChangeInstallationDirectory") is True, (
            "nsis.allowToChangeInstallationDirectory must be true"
        )

        artifact = build.get("artifactName", "")
        assert "installer" in artifact.lower(), (
            f"build.artifactName should produce 'installer.exe', got: {artifact!r}"
        )

    def test_no_icon_reference_without_file(self):
        icon_file = ELECTRON_APP / "icon.png"
        pkg_path = ELECTRON_APP / "package.json"
        main_js = ELECTRON_APP / "main.js"

        if icon_file.is_file():
            return  # icon exists, references are fine

        # Icon doesn't exist — make sure it's not referenced
        pkg_text = pkg_path.read_text(encoding="utf-8")
        pkg = json.loads(pkg_text)
        win_icon = pkg.get("build", {}).get("win", {}).get("icon")
        mac_icon = pkg.get("build", {}).get("mac", {}).get("icon")
        assert win_icon is None, f"win.icon references missing file: {win_icon}"
        assert mac_icon is None, f"mac.icon references missing file: {mac_icon}"

        if main_js.is_file():
            js_text = main_js.read_text(encoding="utf-8")
            assert "icon.png" not in js_text, (
                "main.js references icon.png but file doesn't exist"
            )

    def test_pyinstaller_console_false(self):
        spec_path = INSTALLER / "pyinstaller.spec"
        assert spec_path.is_file(), "pyinstaller.spec not found"
        spec_text = spec_path.read_text(encoding="utf-8")

        match = re.search(r"console\s*=\s*(True|False)", spec_text)
        assert match is not None, "No console= setting found in spec"
        assert match.group(1) == "False", (
            "console must be False to prevent visible console window"
        )

    def test_torch_in_excludes(self):
        spec_path = INSTALLER / "pyinstaller.spec"
        assert spec_path.is_file(), "pyinstaller.spec not found"
        spec_text = spec_path.read_text(encoding="utf-8")

        for pkg_name in ("torch", "transformers"):
            pattern = rf"""['"]({re.escape(pkg_name)})['"]"""
            # Find it inside the excludes= list
            excludes_match = re.search(
                r"excludes\s*=\s*\[(.*?)\]", spec_text, re.DOTALL
            )
            assert excludes_match is not None, "No excludes= list found in spec"
            excludes_block = excludes_match.group(1)
            assert re.search(pattern, excludes_block), (
                f"{pkg_name!r} not found in excludes list"
            )

    def test_server_has_main_block(self):
        server_text = (BACKEND / "server.py").read_text(encoding="utf-8")
        assert 'if __name__ == "__main__"' in server_text, (
            "server.py must have a __main__ block for PyInstaller execution"
        )

    def test_name_data_is_package(self):
        init_file = BACKEND / "name_data" / "__init__.py"
        assert init_file.is_file(), (
            "name_data/__init__.py must exist for PyInstaller to treat it as a package"
        )

    # ── Emergent.sh cleanup guards ──────────────────────────

    def test_index_html_no_emergent_scripts(self):
        """index.html must not load any emergent.sh external scripts."""
        index_html = FRONTEND / "public" / "index.html"
        assert index_html.is_file(), "frontend/public/index.html not found"
        text = index_html.read_text(encoding="utf-8")
        assert "emergent.sh" not in text, (
            "index.html still references emergent.sh — "
            "remove the blocking script tag and debug-monitor injection"
        )

    def test_index_html_no_posthog(self):
        """index.html must not contain PostHog analytics."""
        index_html = FRONTEND / "public" / "index.html"
        text = index_html.read_text(encoding="utf-8")
        assert "posthog" not in text.lower(), (
            "index.html still contains PostHog analytics SDK — "
            "remove the tracking script and init call"
        )

    def test_index_html_no_emergent_badge(self):
        """index.html must not contain the 'Made with Emergent' badge."""
        index_html = FRONTEND / "public" / "index.html"
        text = index_html.read_text(encoding="utf-8")
        assert "emergent-badge" not in text, (
            "index.html still contains the emergent-badge element"
        )
        assert "Made with Emergent" not in text, (
            "index.html still contains 'Made with Emergent' text"
        )

    def test_index_html_meta_description_not_emergent(self):
        """Meta description must not attribute the app to emergent.sh."""
        index_html = FRONTEND / "public" / "index.html"
        text = index_html.read_text(encoding="utf-8")
        assert "product of emergent" not in text.lower(), (
            'meta description still says "A product of emergent.sh"'
        )

    def test_no_visual_edits_plugin_directory(self):
        """The visual-edits plugin directory must not exist."""
        visual_edits = FRONTEND / "plugins" / "visual-edits"
        assert not visual_edits.exists(), (
            "frontend/plugins/visual-edits/ still exists — "
            "remove the Emergent dev tooling directory"
        )

    def test_craco_no_visual_edits_reference(self):
        """craco.config.js must not reference the visual-edits plugin."""
        craco = FRONTEND / "craco.config.js"
        if not craco.is_file():
            return
        text = craco.read_text(encoding="utf-8")
        assert "visual-edits" not in text, (
            "craco.config.js still references visual-edits plugin"
        )

    def test_no_emergent_config_directory(self):
        """The .emergent/ directory must not exist."""
        emergent_dir = ROOT / ".emergent"
        assert not emergent_dir.exists(), (
            ".emergent/ directory still exists — "
            "remove the Emergent platform config"
        )

    def test_no_emergent_gitconfig(self):
        """The .gitconfig with Emergent agent credentials must not exist."""
        gitconfig = ROOT / ".gitconfig"
        if not gitconfig.is_file():
            return
        text = gitconfig.read_text(encoding="utf-8")
        assert "emergent" not in text.lower(), (
            ".gitconfig still contains Emergent agent credentials"
        )

    def test_no_package_manager_field_in_frontend(self):
        pkg_path = FRONTEND / "package.json"
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        assert "packageManager" not in pkg, (
            "frontend/package.json still has packageManager field — "
            "this can block npm on Node v24 with corepack"
        )


# ── Post-build tests ────────────────────────────────────────


class TestPostBuild:
    """Tests that verify build artifacts after the pipeline completes."""

    def test_post_build_installer_exe_exists(self):
        exe = DIST / "installer.exe"
        if not DIST.is_dir():
            pytest.skip("dist/ directory not found — build not run yet")
        assert exe.is_file(), f"installer.exe not found in {DIST}"

    def test_post_build_installer_exe_size_reasonable(self):
        exe = DIST / "installer.exe"
        if not exe.is_file():
            pytest.skip("installer.exe not found — build not run yet")
        size_mb = exe.stat().st_size / (1024 * 1024)
        assert 100 < size_mb < 800, (
            f"installer.exe is {size_mb:.0f} MB — "
            "expected 100-800 MB (check torch exclusion if > 500)"
        )

    def test_post_build_backend_dist_has_server_exe(self):
        if not BACKEND_DIST.is_dir():
            pytest.skip("backend_dist/ not found — build not run yet")
        exe = BACKEND_DIST / "server.exe"
        assert exe.is_file(), f"server.exe not found in {BACKEND_DIST}"

    def test_post_build_no_torch_dlls_in_backend_dist(self):
        if not BACKEND_DIST.is_dir():
            pytest.skip("backend_dist/ not found — build not run yet")
        torch_files = list(BACKEND_DIST.rglob("torch*.dll"))
        assert len(torch_files) == 0, (
            f"Found torch DLLs in backend_dist (torch should be excluded): "
            f"{[str(f) for f in torch_files[:5]]}"
        )
