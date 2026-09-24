"""Plasticity bridge binary protocol, based on the public Blender bridge."""

from __future__ import annotations

import struct


TRANSACTION_1 = 0
ADD_1 = 1
UPDATE_1 = 2
DELETE_1 = 3
NEW_VERSION_1 = 10
NEW_FILE_1 = 11
LIST_ALL_1 = 20
LIST_VISIBLE_1 = 22
REFACET_SOME_1 = 26
HANDSHAKE_1 = 100

SOLID = 0
SHEET = 1
WIRE = 2
GROUP = 5
EMPTY = 6


class ProtocolError(RuntimeError):
    """A malformed or unsupported Plasticity bridge packet."""


class Reader:
    def __init__(self, payload, offset=0):
        self.payload = memoryview(payload)
        self.offset = offset

    def _take(self, size):
        end = self.offset + size
        if end > len(self.payload):
            raise ProtocolError("Unexpected end of Plasticity bridge packet")
        value = self.payload[self.offset:end]
        self.offset = end
        return value

    def u32(self):
        return struct.unpack("<I", self._take(4))[0]

    def i32(self):
        return struct.unpack("<i", self._take(4))[0]

    def f32s(self, count):
        return struct.unpack("<%df" % count, self._take(count * 4)) if count else ()

    def i32s(self, count):
        return struct.unpack("<%di" % count, self._take(count * 4)) if count else ()

    def text(self):
        length = self.u32()
        value = self._take(length).tobytes().decode("utf-8")
        self._take((4 - length % 4) % 4)
        return value


def message_type(payload):
    return Reader(payload).u32()


def handshake_message(message_id):
    return struct.pack("<II", HANDSHAKE_1, message_id)


def list_message(message_type_value, message_id):
    return struct.pack("<II", message_type_value, message_id)


def refacet_message(message_id, filename, plasticity_ids, settings):
    """Build the Blender bridge's `REFACET_SOME` request."""
    name = filename.encode("utf-8")
    padding = b"\x00" * ((4 - len(name) % 4) % 4)
    max_sides = 3 if int(settings.get("facet_type", 0)) == 0 else 128
    plane_angle = 0.0 if max_sides == 3 else float(settings.get("plane_angle", 0.785398))
    max_width = float(settings.get("facet_max_width", 0.0))
    min_width = float(settings.get("facet_min_width", 0.0))
    if max_width and max_width < min_width:
        max_width = min_width
    advanced = int(settings.get("facet_settings_mode", settings.get("use_advanced_faceting", 0))) == 1
    tolerance = float(settings.get("facet_tolerance", 0.01))
    angle = float(settings.get("facet_angle", 0.45))
    curve_tolerance = float(settings.get("curve_chord_tolerance", tolerance)) if advanced else tolerance
    curve_angle = float(settings.get("curve_chord_angle", angle)) if advanced else angle
    surface_tolerance = float(settings.get("surface_plane_tolerance", tolerance)) if advanced else tolerance
    surface_angle = float(settings.get("surface_plane_angle", angle)) if advanced else angle
    return (
        struct.pack("<II", REFACET_SOME_1, message_id)
        + struct.pack("<I", len(name)) + name + padding
        + struct.pack("<I", len(plasticity_ids))
        + struct.pack("<%dI" % len(plasticity_ids), *plasticity_ids)
        + struct.pack("<I", int(bool(settings.get("relative_to_bbox", 1))))
        + struct.pack("<f", curve_tolerance)
        + struct.pack("<f", curve_angle)
        + struct.pack("<f", surface_tolerance)
        + struct.pack("<f", surface_angle)
        + struct.pack("<IIf", int(bool(settings.get("match_topology", 1))), max_sides, plane_angle)
        + struct.pack("<fffI", min_width, max_width, max_width * 0.70710678118, 20501)
    )


def parse_handshake(payload):
    reader = Reader(payload)
    if reader.u32() != HANDSHAKE_1:
        raise ProtocolError("Expected handshake response")
    reader.u32()  # echoed request ID
    return set(reader.u32() for _ in range(reader.u32()))


def parse_list_response(payload):
    reader = Reader(payload)
    response_type = reader.u32()
    if response_type not in (LIST_ALL_1, LIST_VISIBLE_1):
        raise ProtocolError("Expected list response, got message type %d" % response_type)
    reader.u32()  # echoed request ID
    status = reader.u32()
    if status != 200:
        raise ProtocolError("Plasticity list request failed with status %d" % status)
    return _parse_transaction(reader)


def parse_refacet_response(payload):
    reader = Reader(payload)
    if reader.u32() != REFACET_SOME_1:
        raise ProtocolError("Expected refacet response")
    reader.u32()
    if reader.u32() != 200:
        raise ProtocolError("Plasticity refacet request failed")
    filename, version, items = reader.text(), reader.u32(), []
    for _ in range(reader.u32()):
        item = {"id": reader.u32(), "version": reader.u32()}
        item["face_facets"] = reader.i32s(reader.u32())
        item["positions"] = reader.f32s(reader.u32())
        item["triangles"] = reader.i32s(reader.u32())
        item["normals"] = reader.f32s(reader.u32())
        item["groups"] = reader.i32s(reader.u32())
        item["face_ids"] = reader.i32s(reader.u32())
        items.append(item)
    return {"filename": filename, "version": version, "items": items}


def _parse_transaction(reader):
    filename = reader.text()
    version = reader.u32()
    count = reader.u32()
    objects = []
    deleted_ids = []
    for _ in range(count):
        item_size = reader.u32()
        item_end = reader.offset + item_size
        if item_end > len(reader.payload):
            raise ProtocolError("Transaction item extends past packet end")
        item = Reader(reader.payload, reader.offset)
        item_type = item.u32()
        if item_type in (ADD_1, UPDATE_1):
            objects.extend(_parse_object_list(item))
        elif item_type == DELETE_1:
            deleted_ids.extend(item.i32s(item.u32()))
        reader.offset = item_end
    return {"filename": filename, "version": version, "objects": objects, "deleted_ids": deleted_ids}


def _parse_object_list(reader):
    objects = []
    for _ in range(reader.u32()):
        object_type = reader.u32()
        result = {
            "type": object_type,
            "id": reader.u32(),
            "version": reader.u32(),
            "parent_id": reader.i32(),
            "material_id": reader.i32(),
            "flags": reader.u32(),
            "name": reader.text(),
            "positions": (), "triangles": (), "normals": (), "groups": (), "face_ids": (),
        }
        if object_type in (SOLID, SHEET):
            position_count = reader.u32()
            result["positions"] = reader.f32s(position_count * 3)
            face_count = reader.u32()
            result["triangles"] = reader.i32s(face_count * 3)
            normal_count = reader.u32()
            result["normals"] = reader.f32s(normal_count * 3)
            result["groups"] = reader.i32s(reader.u32())
            result["face_ids"] = reader.i32s(reader.u32())
        objects.append(result)
    return objects
