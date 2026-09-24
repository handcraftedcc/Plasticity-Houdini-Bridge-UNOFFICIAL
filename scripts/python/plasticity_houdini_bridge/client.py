"""One-shot Plasticity snapshot client."""

from __future__ import annotations


def fetch_geometry(settings):
    """Fetch a single List Visible/List All snapshot and build Houdini geometry."""
    from .geometry import snapshot_to_houdini
    from .protocol import HANDSHAKE_1, LIST_ALL_1, LIST_VISIBLE_1, REFACET_SOME_1, handshake_message, list_message, message_type, parse_handshake, parse_list_response, parse_refacet_response, refacet_message
    from .websocket import BinaryWebSocket, WebSocketError

    server = str(settings.get("server", "localhost:8980"))
    timeout = float(settings.get("timeout_seconds", 15.0))
    try:
        with BinaryWebSocket(server, timeout) as websocket:
            websocket.send_binary(handshake_message(1))
            supported = _receive_until(websocket, HANDSHAKE_1)
            capabilities = parse_handshake(supported)
            requested_type = LIST_ALL_1 if int(settings.get("scope", 0)) else LIST_VISIBLE_1
            if requested_type not in capabilities:
                label = "List All" if requested_type == LIST_ALL_1 else "List Visible"
                raise RuntimeError("Plasticity server does not support %s" % label)
            websocket.send_binary(list_message(requested_type, 2))
            snapshot = parse_list_response(_receive_until(websocket, requested_type))
            if int(settings.get("update_mode", 0)):
                ids = [item["id"] for item in snapshot["objects"] if item["type"] in (0, 1)]
                if REFACET_SOME_1 not in capabilities:
                    raise RuntimeError("Plasticity server does not support re-faceting")
                websocket.send_binary(refacet_message(3, snapshot["filename"], ids, settings))
                refaceted = parse_refacet_response(_receive_until(websocket, REFACET_SOME_1))
                replacements = {item["id"]: item for item in refaceted["items"]}
                for item in snapshot["objects"]:
                    replacement = replacements.get(item["id"])
                    if replacement:
                        item.update(replacement)
                snapshot["version"] = refaceted["version"]
    except (OSError, WebSocketError, RuntimeError) as exc:
        import hou
        raise hou.Error("Plasticity bridge: %s" % exc)
    return snapshot_to_houdini(snapshot, settings, server)


def _receive_until(websocket, expected_type):
    # New-file/version notices may arrive before the response being awaited.
    from .protocol import message_type

    while True:
        payload = websocket.receive_binary()
        if message_type(payload) == expected_type:
            return payload
