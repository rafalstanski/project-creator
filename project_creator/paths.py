"""Resolve the runtime locations used by the package (templates, projects, cache)."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def is_dev_mode() -> bool:
    """Return whether the package runs from the source checkout (dev mode).

    Dev mode means a development/editable install, where the repository
    root sits next to the package. A wheel install (e.g. ``uv tool
    install .``) lands in ``site-packages`` without a ``pyproject.toml``.
    """
    return (PROJECT_ROOT / "pyproject.toml").is_file()


def projects_dir() -> Path:
    """Return the directory under which new projects are created.

    Dev mode: the repository's ``projects/`` directory.
    Tool mode: the current working directory.
    """
    if is_dev_mode():
        return PROJECT_ROOT / "projects"
    return Path.cwd().resolve()


def cache_dir() -> Path:
    """Return the directory for runtime caches (e.g. ``java_versions.json``).

    Dev mode: the repository's ``.cache/`` directory.
    Tool mode: ``~/.cache/project-creator`` (POSIX) or
    ``%LOCALAPPDATA%/project-creator`` (Windows).
    """
    if is_dev_mode():
        return PROJECT_ROOT / ".cache"
    return _user_cache_dir()


def _user_cache_dir() -> Path:
    """Return the per-user cache directory used in tool mode."""
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        base = Path(local_appdata) if local_appdata else Path.home()
        return base / "project-creator"
    return Path.home() / ".cache" / "project-creator"
