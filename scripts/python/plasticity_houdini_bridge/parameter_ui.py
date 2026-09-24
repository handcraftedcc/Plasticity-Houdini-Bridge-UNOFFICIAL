"""Houdini spare-parameter setup for Plasticity Python Snippet/Python SOPs."""

from __future__ import annotations


def configure_node(node):
    """Add missing bridge controls to one Python Snippet or Python SOP."""
    import hou

    if node.type().name() not in ("pythonsnippet", "python"):
        raise hou.Error("%s is not a Python Snippet or Python SOP" % node.path())

    group = node.parmTemplateGroup()
    # Replaced by the mutually exclusive Simple/Advanced menu below.
    if group.find("use_advanced_faceting") is not None:
        group.remove("use_advanced_faceting")
    faceting_templates = {
        "facet_settings_mode", "facet_tolerance", "facet_angle", "curve_chord_tolerance",
        "curve_chord_angle", "surface_plane_tolerance", "surface_plane_angle",
        "facet_min_width", "facet_max_width", "plane_angle",
    }
    for template in _templates(hou):
        if group.find(template.name()) is None:
            group.append(template)
        elif template.name() in faceting_templates:
            # Reapply the template so an existing node gets the new
            # Simple/Advanced visibility conditions without losing its value.
            group.replace(template.name(), template)
    if group.find("update_plasticity") is None:
        group.append(_update_button(hou))
    node.setParmTemplateGroup(group)

    if node.type().name() == "python":
        code = node.parm("python")
        if code is None:
            raise hou.Error("The selected Python SOP has no Python Code parameter")
        if not code.evalAsString().strip():
            code.set(
                "from plasticity_houdini_bridge.sop import cook_python_sop\n\n"
                "cook_python_sop(hou.pwd())\n"
            )
    return node


def configure_selected_nodes():
    """Shelf entry point: configure every selected supported SOP."""
    import hou

    nodes = [node for node in hou.selectedNodes() if node.type().name() in ("pythonsnippet", "python")]
    if not nodes:
        hou.ui.displayMessage(
            "Select one or more Python Snippet SOPs or classic Python SOPs.",
            severity=hou.severityType.Warning,
        )
        return ()
    configured, failures = [], []
    for node in nodes:
        try:
            configured.append(configure_node(node))
        except Exception as exc:
            failures.append("%s: %s" % (node.path(), exc))
    if failures:
        hou.ui.displayMessage("Some nodes could not be configured:\n\n" + "\n".join(failures))
    return tuple(configured)


def update_and_cook(node):
    """Advance the explicit update generation and cook the SOP once."""
    import hou

    generation = node.parm("update_generation")
    generation.set(generation.eval() + 1)
    try:
        node.cook(force=True)
    except hou.OperationFailed as exc:
        # Houdini normally reduces Python Snippet failures to the unhelpful
        # "Error while cooking" message in a button callback. Print the node's
        # actual cook errors instead (for example a refused bridge connection).
        details = "\n".join(node.errors()) or str(exc)
        print("Plasticity update failed on %s:\n%s" % (node.path(), details))


def _templates(hou):
    templates = [
        _string(hou, "server", "Plasticity Server", "localhost:8980"),
        _menu(hou, "scope", "Fetch Scope", ("Visible", "All"), 0),
        _menu(hou, "update_mode", "Update Mode", ("Snapshot", "Snapshot Then Re-facet"), 0),
        _float(hou, "timeout_seconds", "Timeout Seconds", 15.0, 1.0, 120.0),
        _float(hou, "unit_scale", "Unit Scale", 1.0, 0.0001, 1000.0),
        _toggle(hou, "import_solids", "Import Solids", True),
        _toggle(hou, "import_sheets", "Import Sheets", True),
        _toggle(hou, "import_normals", "Import Vertex Normals", True),
        _toggle(hou, "create_object_id", "Create Object ID Attribute", True),
        _toggle(hou, "create_face_id", "Create Plasticity Face ID Attribute", True),
        _toggle(hou, "create_group_id", "Create Face Group Attribute", True),
        _toggle(hou, "create_names", "Create Object Name Attribute", True),
        _toggle(hou, "create_parent_id", "Create Parent ID Attribute", True),
        _menu(hou, "facet_type", "Facet Type", ("Triangles", "Ngons"), 0),
        _menu(hou, "facet_settings_mode", "Faceting Settings", ("Simple", "Advanced"), 0),
        _float(hou, "facet_tolerance", "Tolerance", 0.01, 0.0001, 1.0),
        _float(hou, "facet_angle", "Angle (Radians)", 0.45, 0.1, 1.0),
        _toggle(hou, "relative_to_bbox", "Relative to Bounding Box", True),
        _toggle(hou, "match_topology", "Match Topology", True),
        _float(hou, "curve_chord_tolerance", "Edge Chord Tolerance", 0.01, 0.0001, 1.0),
        _float(hou, "curve_chord_angle", "Edge Angle Tolerance (Radians)", 0.45, 0.1, 1.0),
        _float(hou, "surface_plane_tolerance", "Face Plane Tolerance", 0.01, 0.0001, 1.0),
        _float(hou, "surface_plane_angle", "Face Angle Tolerance (Radians)", 0.45, 0.1, 1.0),
        _float(hou, "facet_min_width", "Minimum Width", 0.0, 0.0, 1000.0),
        _float(hou, "facet_max_width", "Maximum Width", 0.0, 0.0, 1000.0),
        _float(hou, "plane_angle", "Plane Angle (Radians)", 0.785398, 0.0, 3.141593),
        _hidden_int(hou, "update_generation", "Update Generation", 0),
        _toggle(hou, "verbose", "Verbose Diagnostics", False),
    ]
    for name in ("facet_tolerance", "facet_angle"):
        _hide_when(templates, name, hou, "{ facet_settings_mode == 1 }")
    for name in (
        "curve_chord_tolerance", "curve_chord_angle", "surface_plane_tolerance",
        "surface_plane_angle", "facet_min_width", "facet_max_width", "plane_angle",
    ):
        _hide_when(templates, name, hou, "{ facet_settings_mode == 0 }")
    return tuple(templates)


def _hide_when(templates, name, hou, condition):
    next(template for template in templates if template.name() == name).setConditional(
        hou.parmCondType.HideWhen, condition
    )


def _update_button(hou):
    template = hou.ButtonParmTemplate("update_plasticity", "Update Plasticity")
    template.setScriptCallback(
        "from plasticity_houdini_bridge.parameter_ui import update_and_cook\n"
        "update_and_cook(kwargs['node'])"
    )
    template.setScriptCallbackLanguage(hou.scriptLanguage.Python)
    return template


def _string(hou, name, label, default):
    return hou.StringParmTemplate(name, label, 1, default_value=(default,))


def _menu(hou, name, label, labels, default):
    return hou.MenuParmTemplate(
        name, label, tuple(str(index) for index in range(len(labels))), tuple(labels), default_value=default
    )


def _toggle(hou, name, label, default):
    return hou.ToggleParmTemplate(name, label, default_value=default)


def _hidden_int(hou, name, label, default):
    template = hou.IntParmTemplate(name, label, 1, default_value=(default,))
    template.hide(True)
    return template


def _float(hou, name, label, default, minimum, maximum):
    return hou.FloatParmTemplate(
        name, label, 1, default_value=(default,), min=minimum, max=maximum,
        min_is_strict=False, max_is_strict=False,
    )
