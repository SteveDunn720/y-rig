from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

_ASSET_ROOT: Path | None = None


def set_asset_root(path: Path | None) -> None:
    _ASSET_ROOT = path


def get_asset_root() -> Path | None:
    return _ASSET_ROOT


@contextmanager
def temp_asset_root(asset_root_path: Path):
    default_asset_root_value = _ASSET_ROOT
    set_asset_root(asset_root_path)
    try:
        yield
    finally:
        set_asset_root(default_asset_root_value)
