"""
Helpers for normalizing gate ACK payloads from ESP32.
"""
from __future__ import annotations

from typing import Any, Dict

from app.utils.timezone import now_local


def gate_ack_status(ack: Dict[str, Any]) -> str:
    status = str(ack.get("status") or "").strip().lower()
    if status in {"opened", "open", "ok", "success", "done"}:
        return "acked"
    if status in {"failed", "fail", "error"}:
        return "failed"
    return "received"


def gate_ack_update_fields(ack: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "gate_ack_status": gate_ack_status(ack),
        "gate_ack_at": now_local(),
        "gate_ack_received_at": ack.get("received_at"),
        "gate_ack_device_id": ack.get("device_id"),
        "gate_ack_result": ack.get("status"),
        "gate_ack_payload": ack,
    }
