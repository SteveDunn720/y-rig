"""
Skinning utilities for Maya meshes.

Provides tools for querying and manipulating skinCluster weights, splitting
weights across joints using spline-based falloff, ngSkinTools2 integration,
and debug visualization of per-vertex influences.
"""

from . import core as core
from . import ng as ng
from . import serialize as serialize
from . import split as split
from . import visualize as visualize
from .core import skin_geometry
from .serialize import export_skin_weights, import_skin_weights

__all__ = [
    "core",
    "ng",
    "serialize",
    "split",
    "visualize",
    "skin_geometry",
    "export_skin_weights",
    "import_skin_weights",
]
