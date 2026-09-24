"""Adapters for Houdini's Python Snippet and classic Python SOP nodes."""

from __future__ import annotations


def cook_python_snippet(node):
    """Return new geometry to a Python Snippet SOP."""
    from .client import fetch_geometry

    return fetch_geometry(_settings(node))


def cook_python_sop(node):
    """Replace the writable output geometry of a classic Python SOP."""
    result = cook_python_snippet(node)
    output = node.geometry()
    output.clear()
    output.merge(result)


def _settings(node):
    names = (
        "server", "scope", "update_mode", "timeout_seconds", "unit_scale", "import_solids",
        "import_sheets", "import_normals", "create_object_id", "create_face_id", "create_group_id",
        "create_names", "create_parent_id", "facet_type", "facet_settings_mode", "facet_tolerance", "facet_angle",
        "relative_to_bbox", "match_topology", "curve_chord_tolerance", "curve_chord_angle",
        "surface_plane_tolerance", "surface_plane_angle", "facet_min_width", "facet_max_width",
        "plane_angle", "update_generation", "verbose",
    )
    return {name: node.parm(name).eval() for name in names if node.parm(name) is not None}
