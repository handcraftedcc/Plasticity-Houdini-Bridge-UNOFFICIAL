"""Paste into a classic Python SOP, or let the shelf setup install it."""

from plasticity_houdini_bridge.sop import cook_python_sop

cook_python_sop(hou.pwd())
