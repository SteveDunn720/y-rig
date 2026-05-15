"""
Skinning utilities for Maya meshes.

Provides tools for querying and manipulating skinCluster weights, splitting
weights across joints using spline-based falloff, ngSkinTools2 integration,
and debug visualization of per-vertex influences.
"""

from . import apply, core, ng, serialize, split, visualize
from .apply import (
    skin_and_apply_ng_weights,
    skin_and_apply_weights,
    skin_and_apply_weights_from_directory,
)
from .core import skin_geometry
from .serialize import export_skin_weights, import_skin_weights

__all__ = [
    "apply",
    "core",
    "ng",
    "serialize",
    "split",
    "visualize",
    "skin_geometry",
    "export_skin_weights",
    "import_skin_weights",
    "skin_and_apply_ng_weights",
    "skin_and_apply_weights",
    "skin_and_apply_weights_from_directory",
]
