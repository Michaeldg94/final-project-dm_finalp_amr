"""Pytest configuration and utilities for test collection.

This module ensures the repository root is on `sys.path` so imports like
`import server...` work when running `pytest` from the project root.
It also exposes a `repo_root` fixture for convenience.
"""

from __future__ import annotations

import pytest
from pathlib import Path
import sys



def _add_repo_root_to_sys_path(root: Path) -> None:
    """Add the repository root to `sys.path` if it's not already present.

    Args:
        root: Absolute path to the repository root (directory that contains
              top-level packages like `server/` and the `tests/` folder).
    """
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


# Compute the repo root as the parent of the `tests/` directory and register it.
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent
_add_repo_root_to_sys_path(_REPO_ROOT)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root (session-scoped).

    Returns:
        The `Path` to the project root, useful for loading test assets, etc.
    """
    return _REPO_ROOT
