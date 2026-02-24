"""Master build script for the PII Redactor standalone installer.

Usage:
    python build_installer.py [--skip-frontend] [--skip-backend] [--platform win|mac|all]

Pipeline:
  1. Build React frontend   → ``backend/frontend_build/``
  2. Build Python backend    → ``backend_dist/``  (via PyInstaller)
  3. Build Electron installer → ``dist/``          (via electron-builder)
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
FRONTEND_BUILD_DEST = BACKEND / "frontend_build"
INSTALLER_DIR = Path(__file__).resolve().parent
ELECTRON_APP = INSTALLER_DIR / "electron-app"


def _run(cmd: list[str], cwd: str | Path | None = None, env: dict | None = None) -> None:
    """Run a command, stream output, raise on failure."""
    merged_env = {**os.environ, **(env or {})}
    print(f"\n> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=merged_env)
    if result.returncode != 0:
        print(f"FAILED (exit {result.returncode}): {' '.join(str(c) for c in cmd)}")
        sys.exit(1)


def step_build_frontend() -> None:
    """Step 1: Build the React frontend to static files."""
    print("\n" + "=" * 60)
    print("Step 1: Building React frontend")
    print("=" * 60)

    if not (FRONTEND / "package.json").exists():
        print("frontend/package.json not found — skipping frontend build.")
        return

    # Detect package manager
    if (FRONTEND / "yarn.lock").exists():
        install_cmd = ["yarn", "install", "--frozen-lockfile"]
        build_cmd = ["yarn", "build"]
    else:
        install_cmd = ["npm", "ci"]
        build_cmd = ["npm", "run", "build"]

    # Set REACT_APP_BACKEND_URL to empty string so the frontend uses
    # relative URLs (both frontend and backend are served from same origin).
    build_env = {"REACT_APP_BACKEND_URL": "", "CI": "true"}

    _run(install_cmd, cwd=FRONTEND)
    _run(build_cmd, cwd=FRONTEND, env=build_env)

    # Copy build output to backend/frontend_build/
    build_output = FRONTEND / "build"
    if not build_output.is_dir():
        print("Frontend build output not found at frontend/build/")
        sys.exit(1)

    if FRONTEND_BUILD_DEST.exists():
        shutil.rmtree(FRONTEND_BUILD_DEST)
    shutil.copytree(build_output, FRONTEND_BUILD_DEST)
    print(f"Frontend copied to {FRONTEND_BUILD_DEST}")


def step_build_backend() -> None:
    """Step 2: Build the Python backend via PyInstaller."""
    print("\n" + "=" * 60)
    print("Step 2: Building Python backend with PyInstaller")
    print("=" * 60)

    _run([sys.executable, str(INSTALLER_DIR / "build_backend.py")])


def step_build_electron(target_platform: str) -> None:
    """Step 3: Build the Electron installer."""
    print("\n" + "=" * 60)
    print("Step 3: Building Electron installer")
    print("=" * 60)

    # Install Electron dependencies
    if (ELECTRON_APP / "yarn.lock").exists():
        _run(["yarn", "install"], cwd=ELECTRON_APP)
    else:
        _run(["npm", "install"], cwd=ELECTRON_APP)

    # Determine platform targets
    if target_platform == "all":
        targets = ["--win", "--mac"]
    elif target_platform == "win":
        targets = ["--win"]
    elif target_platform == "mac":
        targets = ["--mac"]
    else:
        # Auto-detect
        if platform.system() == "Windows":
            targets = ["--win"]
        elif platform.system() == "Darwin":
            targets = ["--mac"]
        else:
            targets = ["--win"]

    _run(
        ["npx", "electron-builder"] + targets,
        cwd=ELECTRON_APP,
    )

    dist_dir = ROOT / "dist"
    if dist_dir.is_dir():
        print(f"\nInstaller output: {dist_dir}")
        for f in sorted(dist_dir.iterdir()):
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name}  ({size_mb:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build PII Redactor installer")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend build")
    parser.add_argument("--skip-backend", action="store_true", help="Skip backend build")
    parser.add_argument(
        "--platform",
        choices=["win", "mac", "all", "auto"],
        default="auto",
        help="Target platform for Electron installer (default: auto-detect)",
    )
    args = parser.parse_args()

    print("PII Redactor — Installer Build Pipeline")
    print("=" * 60)
    print(f"  Project root : {ROOT}")
    print(f"  Platform     : {platform.system()} ({platform.machine()})")
    print(f"  Python       : {sys.version.split()[0]}")
    print()

    if not args.skip_frontend:
        step_build_frontend()
    else:
        print("Skipping frontend build (--skip-frontend)")

    if not args.skip_backend:
        step_build_backend()
    else:
        print("Skipping backend build (--skip-backend)")

    step_build_electron(args.platform)

    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
