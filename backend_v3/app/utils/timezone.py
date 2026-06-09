"""
Project timestamp helpers.

The demo runs in Vietnam local time. Store MongoDB display timestamps as naive
Asia/Ho_Chi_Minh datetimes so existing frontend formatting shows the same
clock time that users see at the gate.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def iso_local(timespec: str = "milliseconds") -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec=timespec)
