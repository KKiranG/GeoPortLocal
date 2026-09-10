"""Cheap device-presence probing used by status polling."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pymobiledevice3 import usbmux

PresenceProbe = Callable[[str], Awaitable[bool | None]]


async def probe_device_presence(identifier: str) -> bool | None:
    """Return True/False when usbmux can answer, otherwise None for unknown.

    A probe failure must not tear down an otherwise healthy session. Only a
    successful enumeration proving that the selected identifier is absent is
    authoritative enough to invalidate idle UI state.
    """
    try:
        devices = await usbmux.list_devices()
    except Exception:
        return None
    return any(device.serial == identifier for device in devices)
