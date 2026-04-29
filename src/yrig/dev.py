import logging
import sys

from yrig.build.mgear_api.reload import reload_components

log = logging.getLogger(__name__)


def reload_yrig() -> None:
    """
    This removes all the yrig modules so that on next import they will be updated.
    Useful when making live changes and wanting to test without re-starting Maya.
    """
    module_names = [name for name in sys.modules if name.startswith("yrig")]
    for name in module_names:
        if name in sys.modules:
            log.info(f"Unloading {name}")
            del sys.modules[name]
    log.info("Reloaded yrig python modules")


def reload() -> None:
    """
    This removes all the yrig modules, as well as reloading the mGear components.
    Useful when making live changes and wanting to test without re-starting Maya.

    IMPORTANT: This does NOT re-import yrig as a library.
    """
    reload_yrig()
    reload_components()
