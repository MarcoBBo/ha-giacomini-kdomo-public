"""Current-program weekly schedules, validated independently of Home Assistant."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .models import ProtocolError, Snapshot

HEAT_LEVELS = (
    ("Antigelo", "tempantifreeze"),
    ("Comfort", "heatingtempcomfort"),
    ("Notte", "heatingtempnight"),
    ("Economy", "heatingtempeconomy"),
    ("Comfort+", "heatingtempcomfortplus"),
    ("Economy+", "tempeconomyplus"),
    ("Stop", None),
)
COOL_LEVELS = (
    ("Comfort", "coolingtempcomfort"),
    ("Notte", "coolingtempnight"),
    ("Economy", "coolingtempeconomy"),
    ("Comfort+", "coolingtempcomfortplus"),
    ("Stop", None),
)


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_days(days: Any, season: str) -> list[list[dict[str, int]]]:
    """A complete Sunday-first week, each day covered by 1–8 consecutive slots."""
    if not isinstance(days, list) or len(days) != 7:
        raise ProtocolError("A complete seven-day schedule is required")
    result: list[list[dict[str, int]] | None] = [None] * 7
    count = len(HEAT_LEVELS if season == "heat" else COOL_LEVELS)
    for day in days:
        if not isinstance(day, dict) or set(day) != {"day", "slots"}:
            raise ProtocolError("Invalid schedule day")
        index, slots = day["day"], day["slots"]
        if not _integer(index) or not 0 <= index <= 6 or result[index] is not None:
            raise ProtocolError("Invalid or duplicate schedule day")
        if not isinstance(slots, list) or not 1 <= len(slots) <= 8:
            raise ProtocolError("Each day needs one to eight slots")
        clean = []
        previous = 0
        for slot in slots:
            if not isinstance(slot, dict) or set(slot) != {"level", "end"}:
                raise ProtocolError("Invalid schedule slot")
            level, end = slot["level"], slot["end"]
            if not _integer(level) or not 0 <= level < count:
                raise ProtocolError("Unknown level for the program season")
            # Cloud 23:59 is represented as 24:00 in the editor. No separate 23:59 boundary.
            if not _integer(end) or not previous < end <= 1440 or end == 1439:
                raise ProtocolError("Schedule ends must increase; use 1440 for the day boundary")
            clean.append({"level": level, "end": end})
            previous = end
        if previous != 1440:
            raise ProtocolError("Every schedule day must cover the full day")
        result[index] = clean
    return result


@dataclass(frozen=True)
class Week:
    program: int
    name: str
    season: str
    metadata: str
    raw_days: tuple[str, ...]
    days: list[list[dict[str, int]]]
    revision: str

    def as_dict(self, state: Snapshot, *, write_enabled: bool) -> dict[str, Any]:
        levels = HEAT_LEVELS if self.season == "heat" else COOL_LEVELS
        return {
            "program": self.program,
            "name": self.name,
            "season": self.season,
            "revision": self.revision,
            "scale": state.scale,
            "write_enabled": write_enabled,
            "days": [{"day": day, "slots": slots} for day, slots in enumerate(self.days)],
            "levels": [
                {"id": i, "name": label, "temperature": state.number(key) if key else None}
                for i, (label, key) in enumerate(levels)
            ],
            "mode": state.integer("mode"),
            "status": state.integer("status"),
        }


def decode_week(state: Snapshot) -> Week:
    """Reject missing/mixed programs and malformed days; no default week is invented."""
    if not state.online or state.error:
        raise ProtocolError("Device is unavailable")
    program = state.integer("program")
    if program is None or program not in range(6):
        raise ProtocolError("Missing current program")
    metadata = state.values.get(f"prog{program}", "")
    parts = metadata.split(";")
    if (
        len(parts) != 4
        or parts[0] != str(program)
        or parts[2] not in ("0", "1")
        or parts[3] != "0"
        or not parts[1]
        or len(parts[1]) > 128
        or any(c in metadata for c in "\r\n\x00")
    ):
        raise ProtocolError("Unsupported program metadata")
    season = "heat" if parts[2] == "0" else "cool"
    raw = []
    days = []
    for day in range(7):
        value = state.values.get(f"progDay{day}", "")
        fields = value.split(";")
        if len(fields) != 18 or fields[:2] != [str(program), str(day)]:
            raise ProtocolError("Incomplete week or days belonging to another program")
        slots = []
        previous = 0
        for pos in range(2, 18, 2):
            level, end = fields[pos : pos + 2]
            if not re.fullmatch(r"[0-6]", level) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", end):
                raise ProtocolError("Malformed schedule time or level")
            minutes = int(end[:2]) * 60 + int(end[3:])
            if previous == 1439 and minutes == 1439:
                continue  # Inactive wire padding; preserve it on unchanged days.
            if minutes <= previous:
                raise ProtocolError("Schedule times do not increase")
            slots.append({"level": int(level), "end": 1440 if minutes == 1439 else minutes})
            previous = minutes
        raw.append(value)
        days.append({"day": day, "slots": slots})
    clean = validate_days(days, season)
    levels = HEAT_LEVELS if season == "heat" else COOL_LEVELS
    revision_values = [metadata, raw, state.scale, [state.values.get(key) for _, key in levels if key]]
    revision = hashlib.sha256(json.dumps(revision_values, separators=(",", ":")).encode()).hexdigest()
    return Week(program, parts[1], season, metadata, tuple(raw), clean, revision)


def schedule_payload(before: Week, days: Any) -> tuple[dict[str, str], list[list[dict[str, int]]], list[int]]:
    """Preserve every unchanged day's exact wire fields in the complete 116-field command."""
    clean = validate_days(days, before.season)
    changed = [i for i in range(7) if clean[i] != before.days[i]]
    fields = before.metadata.split(";")
    for day in range(7):
        if day not in changed:
            fields.extend(before.raw_days[day].split(";")[2:])
            continue
        for slot in clean[day]:
            end = slot["end"]
            fields.extend((str(slot["level"]), "23:59" if end == 1440 else f"{end // 60:02d}:{end % 60:02d}"))
        fields.extend(["0", "23:59"] * (8 - len(clean[day])))
    return {"completeschedule": ";".join(fields)}, clean, changed


def schedule_confirmed(
    before: Snapshot, after: Snapshot, desired: list, changed: list[int], sent_at: float
) -> bool:
    """Check all seven logical days and new timestamps for changed days."""
    try:
        old, new = decode_week(before), decode_week(after)
    except ProtocolError:
        return False
    if old.metadata != new.metadata or before.scale != after.scale or new.days != desired:
        return False
    return all(
        after.timestamps.get(f"progDay{day}", -1)
        >= max(sent_at - 1, before.timestamps.get(f"progDay{day}", -1))
        for day in changed
    )
