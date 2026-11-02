"""Fail-closed device policy for explicitly enabled read-only operation.

Copyright (C) 2026 Kobra Bridge contributors
SPDX-License-Identifier: GPL-3.0-only
"""
import json


class ReadOnlyViolation(PermissionError):
    """The requested operation is unavailable in read-only mode."""


READ_ONLY_GET_PATHS = frozenset({
    "/server/info", "/health", "/printer/info", "/printer/objects/list",
    "/printer/objects/query", "/api/state",
})
READ_ONLY_QUERIES = frozenset({
    ("info", "query"), ("status", "query"), ("print", "query"),
    ("tempature", "query"), ("multiColorBox", "getInfo"),
    ("light", "query"),
})


def parse_read_only(value):
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise ValueError("read_only must be 0/1, false/true, no/yes or off/on")


def validate_read_only_request(msg_type, action, data):
    if (not isinstance(msg_type, str) or not isinstance(action, str)
            or (msg_type, action) not in READ_ONLY_QUERIES or data is not None):
        raise ReadOnlyViolation("Only status queries are allowed in read-only mode")


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def validate_read_only_frame(frame, model_id, device_id):
    """Validate the entire outgoing packet before any socket write.

    Only a single QoS-0, non-retained status PUBLISH, the exact device
    subscription, and a PINGREQ may pass. CONNECT is constructed separately
    by the client's TLS/authentication path.
    """
    try:
        if frame == b"\xc0\x00":
            return
        if len(frame) < 2 or frame[0] not in (0x30, 0x82):
            raise ValueError("Unsupported MQTT packet")
        pos, remaining, factor = 1, 0, 1
        for _ in range(4):
            byte = frame[pos]
            pos += 1
            remaining += (byte & 127) * factor
            if not byte & 128:
                break
            factor *= 128
        else:
            raise ValueError("Invalid MQTT remaining length")
        if pos + remaining != len(frame):
            raise ValueError("Incomplete or concatenated MQTT packets")
        body = frame[pos:]
        if frame[0] == 0x82:
            body = body[2:]  # packet identifier
        size = int.from_bytes(body[:2], "big")
        if len(body) < 2 + size:
            raise ValueError("Invalid MQTT topic")
        topic = body[2:2+size].decode("utf-8")
        payload = body[2+size:]
        prefix = "anycubic/anycubicCloud/v1"
        if frame[0] == 0x82:
            if topic != f"{prefix}/printer/public/{model_id}/{device_id}/#" or payload != b"\x00":
                raise ValueError("Unexpected subscription")
            return
        data = json.loads(payload, object_pairs_hook=_unique_fields)
        if (not isinstance(data, dict) or "data" not in data
                or set(data) - {"type", "action", "data", "msgid", "timestamp"}):
            raise ValueError("Invalid query payload")
        validate_read_only_request(data.get("type"), data.get("action"), data["data"])
        expected = {f"{prefix}/{sender}/printer/{model_id}/{device_id}/{data['type']}"
                    for sender in ("slicer", "web")}
        if topic not in expected:
            raise ValueError("Unexpected device or topic")
    except (ValueError, IndexError, KeyError, TypeError, UnicodeError) as exc:
        raise ReadOnlyViolation("Outgoing MQTT packet blocked in read-only mode") from exc
