import os
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]


def base_path() -> Path:
    """Return the base directory of the app (handles PyInstaller _MEIPASS)."""
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base:
        return Path(frozen_base)
    return _ROOT


def resource_path(*parts: str) -> Path:
    """
    Build an absolute path for resources that works in dev and frozen exe.

    Example:
        resource_path("app", "ui", "styles", "dark_styles.qss")
    """
    return base_path().joinpath(*parts)


def ensure_dll_directory(path: Path):
    """Add a folder to DLL search paths on Windows (no-op if missing)."""
    if not path or not path.is_dir():
        return
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(path))
    # Always prepend to PATH as well, since some libs only scan PATH
    os.environ["PATH"] = f"{str(path)}{os.pathsep}{os.environ.get('PATH', '')}"


def appdata_dir(app_name: str = "VisoMaster") -> Path:
    """Return a writable per-user data folder."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    target = base / app_name
    target.mkdir(parents=True, exist_ok=True)
    return target
