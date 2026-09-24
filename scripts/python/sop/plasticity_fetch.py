"""Paste into a Python Snippet SOP, then run the bridge shelf setup."""

from plasticity_houdini_bridge.sop import cook_python_snippet

return cook_python_snippet(hou.pwd())
