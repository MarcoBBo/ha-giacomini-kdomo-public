import math

import pytest

from custom_components.kdomo.models import (
    ProtocolError,
    decode_measurements,
    format_target,
    fresh_confirmation,
    settings_payload,
)

from .conftest import snapshot


def test_precedence_and_newest_duplicate():
    state = decode_measurements(
        [
            {"parameter": "temperature", "when": 5, "intVal": 19, "doubleVal": 20.2, "stringVal": "21.1"},
            {"parameter": "temperature", "when": 4, "doubleVal": 15},
            {"parameter": "humidity", "when": 6, "doubleVal": 50, "stringVal": None},
        ],
        online=True,
    )
    assert state.number("temperature") == 21.1
    assert state.number("humidity") == 50
    assert state.timestamps["temperature"] == 5


@pytest.mark.parametrize(
    "rows", [{}, [None], [{"parameter": "mode"}], [{"parameter": "mode", "when": math.nan}]]
)
def test_invalid_measurements(rows):
    with pytest.raises(ProtocolError):
        decode_measurements(rows, online=True)


@pytest.mark.parametrize(
    ("value", "scale"), [(math.nan, 0), (math.inf, 0), (-1, 0), (36, 0), (31, 1), (96, 1), (20, 2)]
)
def test_reject_invalid_target(value, scale):
    with pytest.raises(ProtocolError):
        format_target(value, scale)


def test_full_group_preserved_and_off_stays_off():
    body = settings_payload(snapshot(program=4, prog4="4;Custom;0;0", fancoil=3), target=22)
    assert body == {"mode": 2, "status": 0, "program": 4, "currentsetpoint": "+22.0", "fancoil": "3"}


def test_heat_turns_on_in_temporary_manual():
    body = settings_payload(snapshot(), target=22, operation="heat")
    assert body["mode"] == 2 and body["status"] == 1 and body["program"] == 0


def test_auto_restores_native_program_without_changing_schedule():
    body = settings_payload(snapshot(mode=2, status=1), operation="auto")
    assert body["mode"] == 1
    assert set(body) == {"mode", "program", "status", "currentsetpoint", "fancoil"}


@pytest.mark.parametrize(
    "state,kwargs",
    [
        (snapshot(online=False), {"target": 22}),
        (snapshot(scale=5), {"target": 22}),
        (snapshot(), {"operation": "cool"}),
        (snapshot(), {"operation": "auto", "target": 22}),
        (snapshot(program=8), {"target": 22}),
        (snapshot(fancoil=""), {"target": 22}),
        (snapshot(mode=5), {"target": 22}),
    ],
)
def test_fail_closed(state, kwargs):
    with pytest.raises(ProtocolError):
        settings_payload(state, **kwargs)


def test_fahrenheit_and_unknown_season():
    assert format_target(72.25, 1) == "+72.3"
    assert snapshot(program=4).season is None
    assert snapshot(program=1).season == "cool"


def test_fresh_confirmation_not_http_ack():
    before = snapshot()
    body = settings_payload(before, target=22, operation="heat")
    assert not fresh_confirmation(before, before, body, 1002)
    assert not fresh_confirmation(before, snapshot(mode=2, status=1, currentsetpoint=22), body, 1002)
    assert fresh_confirmation(before, snapshot(mode=2, status=1, currentsetpoint=22, when=1003), body, 1002)
