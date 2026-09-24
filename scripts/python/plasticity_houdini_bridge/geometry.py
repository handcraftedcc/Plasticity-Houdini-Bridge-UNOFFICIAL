"""Convert decoded Plasticity snapshot records into Houdini polygon geometry."""

from __future__ import annotations

from array import array

from .protocol import SHEET, SOLID


def snapshot_to_houdini(snapshot, settings, server):
    import hou

    scale = float(settings.get("unit_scale", 1.0))
    allowed = set()
    if settings.get("import_solids", 1):
        allowed.add(SOLID)
    if settings.get("import_sheets", 1):
        allowed.add(SHEET)
    objects = [item for item in snapshot["objects"] if item["type"] in allowed]
    geometry = hou.Geometry()
    positions, polygons, normals = [], [], []
    object_ids, versions, face_ids, group_ids, parent_ids, material_ids, flags, names = [], [], [], [], [], [], [], []
    point_offset = 0
    for item in objects:
        local_positions = item["positions"]
        positions.extend((local_positions[index] * scale, local_positions[index + 1] * scale, local_positions[index + 2] * scale) for index in range(0, len(local_positions), 3))
        indices = item["triangles"]
        for start, end in _polygon_spans(indices, item.get("face_facets", ())):
            # Plasticity's facet winding is opposite Houdini's. Reverse the
            # complete polygon, not merely each group of three corners.
            source_indices = list(indices[start:end])
            source_indices.reverse()
            # Re-faceted ngons can repeat vertices. Houdini cannot form a
            # useful polygon from duplicate corners, so retain first uses only.
            kept_indices = []
            seen_positions = set()
            for source_index in source_indices:
                position = tuple(local_positions[source_index * 3:source_index * 3 + 3])
                if position not in seen_positions:
                    seen_positions.add(position)
                    kept_indices.append(source_index)
            if len(kept_indices) < 3:
                continue
            polygons.append(tuple(point_offset + source_index for source_index in kept_indices))
            face_id, group_id = _face_group_at(item, start)
            object_ids.append(item["id"])
            versions.append(item["version"])
            face_ids.append(face_id)
            group_ids.append(group_id)
            parent_ids.append(item["parent_id"])
            material_ids.append(item["material_id"])
            flags.append(item["flags"])
            names.append(item["name"])
            if settings.get("import_normals", 1) and item["normals"]:
                source_normals = item["normals"]
                normals.extend(
                    source_normals[source_index * 3:source_index * 3 + 3]
                    for source_index in kept_indices
                )
        point_offset += len(local_positions) // 3
    if positions:
        points = geometry.createPoints(tuple(positions))
        geometry.createPolygons(tuple(tuple(points[index] for index in polygon) for polygon in polygons))
    if normals and len(normals) == sum(len(polygon) for polygon in polygons):
        geometry.addAttrib(hou.attribType.Vertex, "N", (0.0, 0.0, 0.0), transform_as_normal=True)
        geometry.setVertexFloatAttribValuesFromString("N", array("f", (value for normal in normals for value in normal)))
    _prim_int(geometry, hou, "plasticity_id", object_ids, settings.get("create_object_id", 1))
    _prim_int(geometry, hou, "plasticity_version", versions, settings.get("create_object_id", 1))
    _prim_int(geometry, hou, "plasticity_face_id", face_ids, settings.get("create_face_id", 1))
    _prim_int(geometry, hou, "plasticity_face_group", group_ids, settings.get("create_group_id", 1))
    _prim_int(geometry, hou, "plasticity_parent_id", parent_ids, settings.get("create_parent_id", 1))
    _prim_int(geometry, hou, "plasticity_material_id", material_ids, settings.get("create_object_id", 1))
    _prim_int(geometry, hou, "plasticity_flags", flags, settings.get("create_object_id", 1))
    if names and settings.get("create_names", 1):
        geometry.addAttrib(hou.attribType.Prim, "name", "")
        geometry.setPrimStringAttribValues("name", names)
    _detail(geometry, hou, "plasticity_filename", snapshot["filename"])
    _detail(geometry, hou, "plasticity_file_version", str(snapshot["version"]))
    _detail(geometry, hou, "plasticity_server", server)
    _detail(geometry, hou, "plasticity_import_stats", "%d objects, %d points, %d polygons" % (len(objects), len(positions), len(polygons)))
    return geometry


def _polygon_spans(indices, face_facets):
    """Return corner spans; an empty facet array means triangle output."""
    if not face_facets:
        return tuple((start, start + 3) for start in range(0, len(indices), 3))
    starts = [0]
    starts.extend(index for index in range(1, len(face_facets)) if face_facets[index] != face_facets[index - 1])
    return tuple((start, starts[index + 1] if index + 1 < len(starts) else len(indices)) for index, start in enumerate(starts))


def _face_group_at(item, loop_start):
    groups, ids = item["groups"], item["face_ids"]
    for group_index in range(min(len(ids), len(groups) // 2)):
        start, count = groups[group_index * 2:group_index * 2 + 2]
        if start <= loop_start < start + count:
            return ids[group_index], group_index
    return -1, -1


def _prim_int(geometry, hou, name, values, enabled):
    if enabled and values:
        geometry.addAttrib(hou.attribType.Prim, name, 0)
        geometry.setPrimIntAttribValues(name, values)


def _detail(geometry, hou, name, value):
    geometry.addAttrib(hou.attribType.Global, name, "")
    geometry.setGlobalAttribValue(name, value)
