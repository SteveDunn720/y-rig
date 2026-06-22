from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from yrig.build.scope import BuildScope

_ASSET_ROOT: Path | None = None
_BUILD_SCOPE: BuildScope | None = None


def set_asset_root(path: Path | None) -> None:
    global _ASSET_ROOT
    _ASSET_ROOT = path


def get_asset_root() -> Path | None:
    return _ASSET_ROOT


def set_build_scope(scope: BuildScope | None) -> None:
    global _BUILD_SCOPE
    _BUILD_SCOPE = scope


def get_build_scope() -> BuildScope | None:
    return _BUILD_SCOPE


@contextmanager
def temp_asset_root(asset_root_path: Path, dev_build: bool = False) -> Generator[None, None, None]:
    """Temporarily set the asset root, restoring it afterward unless dev_build is True."""
    default_asset_root_value = _ASSET_ROOT
    set_asset_root(asset_root_path)
    try:
        yield
    finally:
        if not dev_build:
            set_asset_root(default_asset_root_value)


@contextmanager
def temp_build_scope(
    build_scope: BuildScope | None, dev_build: bool = False
) -> Generator[None, None, None]:
    """Temporarily set the build scope, restoring it afterward unless dev_build is True."""
    default_build_scope = _BUILD_SCOPE
    set_build_scope(build_scope)
    try:
        yield
    finally:
        if not dev_build:
            set_build_scope(default_build_scope)
