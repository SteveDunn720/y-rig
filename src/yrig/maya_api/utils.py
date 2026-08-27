import logging

from maya import cmds
from maya.api.OpenMaya import MDagPath, MObject, MSelectionList

log = logging.getLogger(__name__)

_loaded_plugin_cache: set[str] = set()


def ensure_plugin_loaded(plugin: str) -> None:
    if plugin not in _loaded_plugin_cache:
        if not cmds.pluginInfo(plugin, query=True, loaded=True):
            cmds.loadPlugin(plugin)
            log.info(f"Loaded plugin: {plugin}")
        _loaded_plugin_cache.add(plugin)


def get_dag_path(node: str) -> MDagPath:
    selection = MSelectionList()
    selection.add(node)
    try:
        dag_path: MDagPath = selection.getDagPath(0)
    except RuntimeError as exc:
        raise RuntimeError(f"Couldn't resolve an MDagPath for {node}") from exc
    return dag_path


def get_depend_node(node: str) -> MObject:
    selection = MSelectionList()
    selection.add(node)
    try:
        depend_node: MObject = selection.getDependNode(0)
    except RuntimeError as exc:
        raise RuntimeError(f"Couldn't resolve an MObject for {node}") from exc
    return depend_node
