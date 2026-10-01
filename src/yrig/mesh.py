# ruff: noqa: T201
from maya import cmds
from maya.api import OpenMaya as om

from yrig.name import format_item_count


def mesh_topology_signature(mesh: str) -> tuple:
    selection = om.MSelectionList()
    selection.add(mesh)

    dag_path = selection.getDagPath(0)
    fn_mesh = om.MFnMesh(dag_path)

    vertex_count = fn_mesh.numVertices
    polygon_count = fn_mesh.numPolygons
    polygon_counts, polygon_connects = fn_mesh.getVertices()

    return (
        vertex_count,
        polygon_count,
        tuple(polygon_counts),
        tuple(polygon_connects),
    )


def have_same_topology_signature(mesh_a: str, mesh_b: str) -> bool:
    return mesh_topology_signature(mesh_a) == mesh_topology_signature(mesh_b)


def compare_namespace_meshes(namespace_a: str, namespace_b: str) -> None:
    """Compare vertex order of same-named meshes between two namespaces"""
    original_file = cmds.file(query=True, sceneName=True)

    meshes_a = cmds.ls(f"{namespace_a}:*", type="mesh", long=True) or []
    meshes_b = cmds.ls(f"{namespace_b}:*", type="mesh", long=True) or []

    meshes_a = {
        mesh.rsplit("|", 1)[-1].removeprefix(f"{namespace_a}:"): mesh
        for mesh in meshes_a
        if not cmds.getAttr(f"{mesh}.intermediateObject")
    }
    meshes_b = {
        mesh.rsplit("|", 1)[-1].removeprefix(f"{namespace_b}:"): mesh
        for mesh in meshes_b
        if not cmds.getAttr(f"{mesh}.intermediateObject")
    }

    common_names = sorted(meshes_a.keys() & meshes_b.keys())

    matching = []
    mismatched = []

    for name in common_names:
        if have_same_topology_signature(meshes_a[name], meshes_b[name]):
            matching.append(name)
        else:
            mismatched.append(name)

    missing_a = sorted(meshes_b.keys() - meshes_a.keys())
    missing_b = sorted(meshes_a.keys() - meshes_b.keys())

    if mismatched:
        print("\nMISMATCHED:")
        for name in mismatched:
            print(f"  - {name}")

    if missing_a:
        print(
            f"\nMISSING FROM {namespace_a} ({format_item_count(len(missing_a), 'mesh', 'meshes')}): "
        )
        for name in missing_a:
            print(f"  - {name}")

    if missing_b:
        print(
            f"\nMISSING FROM {namespace_b} ({format_item_count(len(missing_b), 'mesh', 'meshes')}):"
        )
        for name in missing_b:
            print(f"  - {name}")
