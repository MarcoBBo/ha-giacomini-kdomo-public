"""Typed wire decoding and conservative topic 02 construction; no HA dependency."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from .const import PRESET_GROUPS


class KdomoError(Exception):
    """A sanitized service error. Never contains server bodies or credentials."""


class AuthenticationError(KdomoError):
    """The cloud rejected authentication."""


class PrivacyError(KdomoError):
    """Privacy acceptance must be completed in the official app."""


class ProtocolError(KdomoError):
    """A response or command does not match the supported protocol."""


class RateLimitError(KdomoError):
    """The cloud asked the client to slow down."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__("Cloud rate limit reached")
        self.retry_after = retry_after


class CommandUncertainError(KdomoError):
    """A command may have been sent; do not replay it automatically."""


class VerificationError(KdomoError):
    """The requested state was not confirmed by fresh cloud measurements."""


@dataclass(frozen=True)
class Device:
    plant_id: str
    serial: str
    name: str

    @property
    def key(self) -> str:
        return f"{self.plant_id}:{self.serial}"


@dataclass(frozen=True)
class Snapshot:
    values: dict[str, str] = field(default_factory=dict)
    timestamps: dict[str, float] = field(default_factory=dict)
    online: bool = False
    error: bool = False

    def number(self, key: str) -> float | None:
        try:
            value = float(self.values[key])
            return value if math.isfinite(value) else None
        except (KeyError, TypeError, ValueError):
            return None

    def integer(self, key: str) -> int | None:
        number = self.number(key)
        return int(number) if number is not None and number.is_integer() else None

    @property
    def scale(self) -> int | None:
        return self.integer("scale")

    @property
    def season(self) -> str | None:
        program = self.integer("program")
        parts = self.values.get(f"prog{program}", "").split(";")
        if len(parts) != 4 or parts[0] != str(program):
            return None
        return {"0": "heat", "1": "cool"}.get(parts[2])


def decode_measurements(rows: Any, *, online: bool) -> Snapshot:
    """Keep APK precedence stringVal > doubleVal > intVal, newest duplicate first."""
    if not isinstance(rows, list):
        raise ProtocolError("Expected a measurement array")
    values: dict[str, str] = {}
    timestamps: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("parameter"), str):
            raise ProtocolError("Invalid measurement record")
        key = row["parameter"]
        timestamp = row.get("when")
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise ProtocolError("Missing measurement timestamp")
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ProtocolError("Invalid measurement timestamp")
        value = next((row[k] for k in ("stringVal", "doubleVal", "intVal") if row.get(k) is not None), None)
        if value is None:
            continue
        if isinstance(value, (dict, list, bool)):
            raise ProtocolError("Invalid measurement value")
        if timestamp >= timestamps.get(key, -1):
            values[key] = str(value)
            timestamps[key] = float(timestamp)
    return Snapshot(values, timestamps, online)


def format_target(value: Any, scale: int) -> str:
    """Apply APK UI bounds and one decimal wire precision, without silent clamping."""
    try:
        number = Decimal(str(value))
        if scale not in (0, 1):
            raise ProtocolError("Unsupported temperature scale")
        low, high = (Decimal(0), Decimal(35)) if scale == 0 else (Decimal(32), Decimal(95))
        if not number.is_finite() or not low <= number <= high:
            raise ProtocolError("Target temperature outside supported bounds")
        return "+" + format(number.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), "04.1f")
    except (InvalidOperation, TypeError, ValueError) as err:
        raise ProtocolError("Invalid target temperature") from err


def settings_payload(
    state: Snapshot,
    *,
    target: Any = None,
    operation: str | None = None,
) -> dict[str, Any]:
    """Full read/modify/write group; only auto, temporary manual, on and off."""
    if not state.online or state.error:
        raise ProtocolError("Device is unavailable")
    mode, program, status = (state.integer(k) for k in ("mode", "program", "status"))
    if mode not in (0, 1, 2) or program not in range(6) or status not in (0, 1, 2):
        raise ProtocolError("Incomplete or unsupported settings")
    fancoil = state.values.get("fancoil")
    if not fancoil or len(fancoil) > 16 or any(c in fancoil for c in ";\r\n"):
        raise ProtocolError("Missing or invalid fan-coil setting")
    current = state.number("currentsetpoint")
    if current is None or state.scale not in (0, 1):
        raise ProtocolError("Missing target or temperature scale")
    if operation not in (None, "off", "on", "auto", "heat", "cool"):
        raise ProtocolError("Unsupported operation")
    if operation in ("heat", "cool"):
        if state.season != operation:
            raise ProtocolError("Operation does not match the active K-Domo program season")
        mode, status = 2, 1
    elif operation == "auto":
        mode, status = 1, 1
    elif operation == "on":
        status = 1
        if mode == 0:
            mode = 2  # Do not rely on unvalidated fixed-manual writes.
    elif operation == "off":
        status = 0
    if target is not None:
        if operation == "auto":
            raise ProtocolError("Choose a manual target or automatic schedule separately")
        mode = 2
        current = target
    return {
        "mode": mode,
        "program": program,
        "status": status,
        "currentsetpoint": format_target(current, state.scale),
        "fancoil": fancoil,
    }


def preset_payload(state: Snapshot, parameter: str, value: Any) -> tuple[str, dict[str, Any]]:
    """Build a complete 10/11 group from a fresh read; never supply missing defaults."""
    if not state.online or state.error:
        raise ProtocolError("Device is unavailable")
    if state.scale not in (0, 1):
        raise ProtocolError("Unsupported temperature scale")
    group = next(
        ((topic, keys, ints) for topic, (keys, ints) in PRESET_GROUPS.items() if parameter in keys), None
    )
    if group is None:
        raise ProtocolError("Unsupported preset temperature")
    topic, keys, integers = group
    payload: dict[str, Any] = {}
    for key in keys:
        current = state.number(key)
        if current is None:
            raise ProtocolError("Incomplete preset temperature group; refresh K-Domo first")
        formatted = format_target(current, state.scale)
        if Decimal(formatted) != Decimal(state.values[key]):
            raise ProtocolError("Preset precision cannot be preserved")
        payload[key] = formatted
    for key in integers:
        current = state.integer(key)
        if current is None or not -(2**31) <= current < 2**31:
            raise ProtocolError("Incomplete preset configuration; refresh K-Domo first")
        payload[key] = current
    payload[parameter] = format_target(value, state.scale)
    return topic, payload


def values_match(state: Snapshot, payload: dict[str, Any]) -> bool:
    """Compare numeric wire forms, including signed setpoint strings."""
    for key, value in payload.items():
        try:
            if Decimal(state.values[key]) != Decimal(str(value)):
                return False
        except (KeyError, InvalidOperation):
            if state.values.get(key) != str(value):
                return False
    return True


def fresh_confirmation(
    before: Snapshot,
    after: Snapshot,
    payload: dict[str, Any],
    sent_at: float,
) -> bool:
    """Require desired values and post-command timestamps for changed parameters."""
    if not after.online or not values_match(after, payload):
        return False
    for key, value in payload.items():
        try:
            changed = Decimal(before.values[key]) != Decimal(str(value))
        except (KeyError, InvalidOperation):
            changed = before.values.get(key) != str(value)
        if changed and (
            after.timestamps.get(key, -1) < sent_at - 1
            or after.timestamps.get(key, -1) < before.timestamps.get(key, -1)
        ):
            return False
    return True
