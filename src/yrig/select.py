from collections.abc import Generator
from contextlib import contextmanager

from maya import cmds


@contextmanager
def maintain_selection() -> Generator[None, None, None]:
    selection = cmds.ls(selection=True, long=True, ufeObjects=True, absoluteName=True)
    try:
        yield
    finally:
        cmds.select(*selection, replace=True)
