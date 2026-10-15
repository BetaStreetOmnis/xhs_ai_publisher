#!/usr/bin/env python3
"""Build the desktop app with Nuitka standalone mode."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "XHS-AI-Publisher"
DEFAULT_OUTPUT_DIR = (
    str(Path(tempfile.gettempdir()) / "xhs-nuitka-dist")
    if platform.system() == "Darwin"
    else "dist-nuitka"
)


def _python_supported() -> bool:
    return (3, 10) <= sys.version_info[:2] < (3, 13)


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


def clean_outputs(output_dir: str = DEFAULT_OUTPUT_DIR) -> None:
    for name in [
        "build",
        output_dir,
        "main.build",
        "main.dist",
        "main.onefile-build",
        f"{APP_NAME}.build",
        f"{APP_NAME}.dist",
        f"{APP_NAME}.onefile-build",
    ]:
        _remove_path(ROOT / name)


def clear_macos_xattrs(path: Path) -> None:
    """Remove Finder/resource-fork metadata that breaks macOS codesign."""
    if platform.system() != "Darwin" or not path.exists():
        return
    subprocess.run(["xattr", "-cr", str(path)], check=False)


def finalize_outputs(output_dir: str) -> None:
    if platform.system() == "Darwin":
        output_path = Path(output_dir)
        default_app = output_path / "main.app"
        named_app = output_path / f"{APP_NAME}.app"
        if default_app.exists() and default_app != named_app:
            _remove_path(named_app)
            default_app.rename(named_app)


def existing_data_args() -> list[str]:
    args: list[str] = []
    for name in ["templates", "assets", "images"]:
        if (ROOT / name).exists():
            args.append(f"--include-data-dir={name}={name}")
    if (ROOT / ".env.example").exists():
        args.append("--include-data-files=.env.example=.env.example")
    return args


def build_command(args: argparse.Namespace) -> list[str]:
    if args.onefile:
        mode = "--mode=onefile"
    elif platform.system() == "Darwin":
        # Nuitka 4.x requires app/app-dist mode for PyQt5 on macOS.
        # app-dist still behaves like standalone, but emits a .app bundle.
        mode = "--mode=app-dist"
    else:
        mode = "--mode=standalone"
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--enable-plugin=pyqt5",
        "--include-package=playwright",
        f"--output-dir={args.output_dir}",
        f"--output-filename={APP_NAME}",
    ]
    cmd.insert(3, mode)

    cmd.extend(existing_data_args())

    if args.assume_yes:
        cmd.append("--assume-yes-for-downloads")

    system = platform.system()
    if system == "Windows":
        if not args.with_console:
            cmd.append("--windows-console-mode=disable")
        icon = ROOT / "build" / "icon.ico"
        if icon.exists():
            cmd.append(f"--windows-icon-from-ico={icon}")
    elif system == "Darwin" and not args.onefile:
        cmd.extend(
            [
                f"--macos-app-name={APP_NAME}",
            ]
        )
        icon = ROOT / "build" / "icon.icns"
        if icon.exists():
            cmd.append(f"--macos-app-icon={icon}")

    cmd.append("main.py")
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Nuitka standalone release.")
    parser.add_argument("--clean", action="store_true", help="Remove previous Nuitka outputs first.")
    parser.add_argument("--onefile", action="store_true", help="Build onefile mode. Standalone is the default.")
    parser.add_argument("--with-console", action="store_true", help="Keep console window on Windows.")
    parser.add_argument("--assume-yes", action="store_true", help="Allow Nuitka dependency downloads without prompts.")
    parser.add_argument("--output-dir", default=os.getenv("XHS_NUITKA_OUTPUT_DIR", DEFAULT_OUTPUT_DIR), help="Directory for Nuitka build output.")
    parser.add_argument("--dry-run", action="store_true", help="Print the Nuitka command without running it.")
    parsed = parser.parse_args()

    if not _python_supported() and not parsed.dry_run:
        print(
            f"Unsupported Python: {sys.version.split()[0]}. "
            "Use Python 3.10-3.12 for this project, preferably 3.11/3.12.",
            file=sys.stderr,
        )
        return 2
    if not _python_supported() and parsed.dry_run:
        print(
            f"Warning: current Python is {sys.version.split()[0]}; real builds require Python 3.10-3.12.",
            file=sys.stderr,
        )

    if parsed.clean:
        clean_outputs(parsed.output_dir)

    if platform.system() == "Darwin":
        for name in ["templates", "assets", "images", ".env.example", "main.py", "src"]:
            clear_macos_xattrs(ROOT / name)

    cmd = build_command(parsed)
    print("Nuitka command:")
    print(" ".join(cmd))

    if parsed.dry_run:
        return 0

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("COPYFILE_DISABLE", "1")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
    finalize_outputs(parsed.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
