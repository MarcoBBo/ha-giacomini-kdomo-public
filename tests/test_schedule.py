"""Weekly wire decoding, strict validation and verified HA schedule actions."""

import asyncio
import copy
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError, Unauthorized

from custom_components.kdomo.const import DOMAIN
from custom_components.kdomo.models import AuthenticationError, ProtocolError, RateLimitError, Snapshot
from custom_components.kdomo.schedule import decode_week, schedule_confirmed, schedule_payload, validate_days

from .conftest import DEVICE, snapshot
from .test_integration import setup


def schedule_snapshot(*, when=1000, **changes):
    program = int(changes.get("program", 0))
    slots = "2;06:30;1;09:00;3;18:00;4;23:00;2;23:59;0;23:59;0;23:59;0;23:59"
    values = {f"progDay{d}": f"{program};{d};{slots}" for d in range(7)}
    if program == 1:
        values = {
            k: v.replace("2;06:30;1;09:00;3;18:00;4;23:00;2;23:59", "1;06:30;0;09:00;2;18:00;3;23:00;1;23:59")
            for k, v in values.items()
        }
    values.update(changes)
    return snapshot(when=when, heatingtempcomfort=21, heatingtempcomfortplus=22, **values)


def edited_week(state=None):
    before = state or schedule_snapshot()
    week = decode_week(before)
    days = week.as_dict(before, write_enabled=True)["days"]
    days = copy.deepcopy(days)
    days[1]["slots"][1]["end"] = 570
    body, desired, changed = schedule_payload(week, days)
    fields = body["completeschedule"].split(";")
    updates = {
        f"progDay{d}": ";".join([str(week.program), str(d)] + fields[4 + d * 16 : 20 + d * 16])
        for d in range(7)
    }
    return week, days, body, desired, changed, schedule_snapshot(when=1003, **updates)


def test_decode_roundtrip_and_wire_sunday_first():
    state = schedule_snapshot()
    week = decode_week(state)
    assert week.name == "Winter" and week.season == "heat"
    assert week.days[0][-1] == {"level": 2, "end": 1440}
    data = week.as_dict(state, write_enabled=True)
    assert data["levels"][1]["temperature"] == 21
    assert data["levels"][-1]["temperature"] is None
    body, desired, changed = schedule_payload(week, data["days"])
    assert not changed and desired == week.days
    fields = body["completeschedule"].split(";")
    assert len(fields) == 116 and fields[:4] == ["0", "Winter", "0", "0"]
    for d in range(7):
        assert fields[4 + 16 * d : 20 + 16 * d] == state.values[f"progDay{d}"].split(";")[2:]
    assert decode_week(schedule_snapshot(when=5000)).revision == week.revision


def test_cooling_levels_are_not_heating_levels():
    state = schedule_snapshot(program=1)
    week = decode_week(state)
    assert week.season == "cool"
    assert [level["name"] for level in week.as_dict(state, write_enabled=False)["levels"]] == [
        "Comfort",
        "Notte",
        "Economy",
        "Comfort+",
        "Stop",
    ]
    days = copy.deepcopy(week.as_dict(state, write_enabled=False)["days"])
    days[0]["slots"][0]["level"] = 5
    with pytest.raises(ProtocolError, match="Unknown level"):
        schedule_payload(week, days)


@pytest.mark.parametrize(
    "changes",
    [
        {"progDay3": ""},
        {"progDay3": "1;3;2;23:59"},
        {"prog0": "0;bad;name;0;0"},
        {"prog0": "0;Winter;0;1"},
        {"program": 6},
        {"online": False},
        {"progDay1": "0;1;2;25:00;" + "0;23:59;" * 6 + "0;23:59"},
        {"progDay1": "0;1;2;06:00;1;05:00;0;23:59;0;23:59;0;23:59;0;23:59;0;23:59;0;23:59"},
        {"progDay1": "0;1;2;00:00;1;05:00;0;23:59;0;23:59;0;23:59;0;23:59;0;23:59;0;23:59"},
        {"progDay1": "0;1;2;06:00;1;05:00;0;23:58;0;23:58;0;23:58;0;23:58;0;23:58;0;23:58"},
    ],
)
def test_invalid_cloud_week_refused(changes):
    with pytest.raises(ProtocolError):
        decode_week(schedule_snapshot(**changes))


def test_missing_program_and_invalid_level_time():
    before = schedule_snapshot()
    for key, value in [
        ("program", "bad"),
        ("progDay0", before.values["progDay0"].replace("2;06:30", "9;06:30")),
        ("progDay0", before.values["progDay0"].replace("2;06:30", "2;6:30")),
    ]:
        state = Snapshot({**before.values, key: value}, before.timestamps, True)
        with pytest.raises(ProtocolError):
            decode_week(state)


@pytest.mark.parametrize(
    "kind", ["missing", "duplicate", "empty", "too_many", "level", "end", "boolean", "no_midnight", "extra"]
)
def test_invalid_editor_input(kind):
    state = schedule_snapshot()
    week = decode_week(state)
    days = copy.deepcopy(week.as_dict(state, write_enabled=True)["days"])
    if kind == "missing":
        days.pop()
    elif kind == "duplicate":
        days[1]["day"] = 0
    elif kind == "empty":
        days[1]["slots"] = []
    elif kind == "too_many":
        days[1]["slots"] *= 2
    elif kind == "level":
        days[1]["slots"][0]["level"] = 7
    elif kind == "end":
        days[1]["slots"][0]["end"] = 1439
    elif kind == "boolean":
        days[1]["day"] = True
    elif kind == "no_midnight":
        days[1]["slots"][-1]["end"] = 1438
    else:
        days[1]["slots"][0]["extra"] = 1
    with pytest.raises(ProtocolError):
        validate_days(days, "heat")


def test_changed_day_encoded_others_exact_and_confirmation():
    week, days, body, desired, changed, after = edited_week()
    assert changed == [1]
    fields = body["completeschedule"].split(";")
    assert len(fields) == 116 and fields[4 + 16 + 3] == "09:30"
    before = schedule_snapshot()
    assert schedule_confirmed(before, after, desired, changed, 1002)
    stale = Snapshot(after.values, before.timestamps, True)
    assert not schedule_confirmed(before, stale, desired, changed, 1002)
    assert not schedule_confirmed(before, schedule_snapshot(online=False), desired, changed, 1002)
    assert not schedule_confirmed(before, schedule_snapshot(prog0="0;Other;0;0"), desired, changed, 1002)
    assert not schedule_confirmed(before, schedule_snapshot(scale=1), desired, changed, 1002)


async def schedule_setup(hass, entry, client, *, enabled=True):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, options={"write_enabled": enabled, "schedule_write_enabled": enabled}
    )
    client.async_state.return_value = schedule_snapshot()
    coordinator = await setup(hass, entry)
    entity = next(s.entity_id for s in hass.states.async_all() if s.domain == "climate")
    return coordinator, entity


async def test_get_action_readonly_and_frontend_registered(hass, entry, mock_client):
    _, entity = await schedule_setup(hass, entry, mock_client, enabled=False)
    data = await hass.services.async_call(
        DOMAIN, "get_schedule", {"entity_id": entity}, blocking=True, return_response=True
    )
    assert data["name"] == "Winter" and not data["write_enabled"]
    assert data["days"][0]["day"] == 0
    mock_client.async_send_schedule.assert_not_awaited()
    assert hass.states.get(entity).attributes["kdomo_schedule_revision"] == data["revision"]
    with pytest.raises(HomeAssistantError, match="disabled"):
        await hass.services.async_call(
            DOMAIN,
            "set_schedule",
            {"entity_id": entity, "revision": data["revision"], "days": data["days"]},
            blocking=True,
        )
    mock_client.async_send_schedule.assert_not_awaited()


async def test_set_action_verified_no_climate_command(hass, entry, mock_client):
    coordinator, entity = await schedule_setup(hass, entry, mock_client)
    week, days, payload, _, _, after = edited_week()
    mock_client.async_state.side_effect = [schedule_snapshot(), after]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0,)),
    ):
        data = await hass.services.async_call(
            DOMAIN,
            "set_schedule",
            {"entity_id": entity, "revision": week.revision, "days": days},
            blocking=True,
            return_response=True,
        )
    assert data["days"] == days and data["revision"] != week.revision
    assert coordinator.data[DEVICE.key].integer("status") == 0
    mock_client.async_send_schedule.assert_awaited_once_with(DEVICE, payload)
    mock_client.async_send_settings.assert_not_awaited()
    mock_client.async_send_presets.assert_not_awaited()


async def test_noop_conflict_and_incomplete_week_never_sent(hass, entry, mock_client):
    coordinator, _ = await schedule_setup(hass, entry, mock_client)
    week, days, _, _, _, after = edited_week()
    original = week.as_dict(schedule_snapshot(), write_enabled=True)["days"]
    await coordinator.async_schedule(DEVICE, days=original, revision=week.revision)
    mock_client.async_state.return_value = after
    with pytest.raises(HomeAssistantError, match="changed"):
        await coordinator.async_schedule(DEVICE, days=days, revision=week.revision)
    mock_client.async_state.return_value = schedule_snapshot(progDay2="")
    with pytest.raises(HomeAssistantError, match="Incomplete"):
        await coordinator.async_schedule(DEVICE, days=days, revision=week.revision)
    mock_client.async_send_schedule.assert_not_awaited()


async def test_ack_without_readback_never_replayed(hass, entry, mock_client):
    coordinator, _ = await schedule_setup(hass, entry, mock_client)
    week, days, _, _, _, _ = edited_week()
    with patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0, 0)):
        with pytest.raises(HomeAssistantError, match="not confirmed"):
            await coordinator.async_schedule(DEVICE, days=days, revision=week.revision)
    mock_client.async_send_schedule.assert_awaited_once()


async def test_two_writers_one_stale_revision(hass, entry, mock_client):
    coordinator, _ = await schedule_setup(hass, entry, mock_client)
    week, days, _, _, _, after = edited_week()
    mock_client.async_state.side_effect = [schedule_snapshot(), after, after]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0,)),
    ):
        result = await asyncio.gather(
            *(coordinator.async_schedule(DEVICE, days=days, revision=week.revision) for _ in range(2)),
            return_exceptions=True,
        )
    assert isinstance(result[0], dict) and isinstance(result[1], HomeAssistantError)
    mock_client.async_send_schedule.assert_awaited_once()


async def test_schedule_backoff_and_reauth(hass, entry, mock_client):
    coordinator, _ = await schedule_setup(hass, entry, mock_client)
    mock_client.async_state.side_effect = RateLimitError(60)
    with pytest.raises(HomeAssistantError, match="rate limit"):
        await coordinator.async_schedule(DEVICE)
    count = mock_client.async_state.await_count
    with pytest.raises(HomeAssistantError, match="rate limit"):
        await coordinator.async_schedule(DEVICE)
    assert mock_client.async_state.await_count == count
    coordinator._next_request_at = 0
    mock_client.async_state.side_effect = AuthenticationError("Rejected")
    with patch.object(type(entry), "async_start_reauth") as reauth:
        with pytest.raises(HomeAssistantError, match="authentication"):
            await coordinator.async_schedule(DEVICE)
        reauth.assert_called_once()


async def test_action_rejects_unknown_entity_unloaded_and_permissions(hass, entry, mock_client):
    _, entity = await schedule_setup(hass, entry, mock_client)
    for entity_id in ["climate.nonexistent", "sensor.example_thermostat_temperature"]:
        with pytest.raises(HomeAssistantError, match="loaded"):
            await hass.services.async_call(
                DOMAIN, "get_schedule", {"entity_id": entity_id}, blocking=True, return_response=True
            )
    user = Mock()
    user.permissions.check_entity.return_value = False
    with patch.object(hass.auth, "async_get_user", AsyncMock(return_value=user)):
        with pytest.raises(Unauthorized):
            await hass.services.async_call(
                DOMAIN,
                "get_schedule",
                {"entity_id": entity},
                blocking=True,
                return_response=True,
                context=Context(user_id="test-user"),
            )
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError, match="loaded"):
        await hass.services.async_call(
            DOMAIN, "get_schedule", {"entity_id": entity}, blocking=True, return_response=True
        )


async def test_separate_schedule_optin_required(hass, entry, mock_client):
    coordinator, _ = await schedule_setup(hass, entry, mock_client, enabled=False)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    week, days, *_ = edited_week()
    with pytest.raises(HomeAssistantError, match="Schedule controls are disabled"):
        await coordinator.async_schedule(DEVICE, days=days, revision=week.revision)
    mock_client.async_send_schedule.assert_not_awaited()


async def test_action_control_permission_and_no_response_call(hass, entry, mock_client):
    _, entity = await schedule_setup(hass, entry, mock_client)
    week = decode_week(schedule_snapshot())
    days = week.as_dict(schedule_snapshot(), write_enabled=True)["days"]
    user = Mock()
    user.permissions.check_entity.side_effect = lambda _entity, policy: policy == "read"
    with patch.object(hass.auth, "async_get_user", AsyncMock(return_value=user)):
        data = await hass.services.async_call(
            DOMAIN,
            "get_schedule",
            {"entity_id": entity},
            blocking=True,
            return_response=True,
            context=Context(user_id="test-user"),
        )
        assert data["revision"] == week.revision
        with pytest.raises(Unauthorized):
            await hass.services.async_call(
                DOMAIN,
                "set_schedule",
                {"entity_id": entity, "revision": week.revision, "days": days},
                blocking=True,
                context=Context(user_id="test-user"),
            )
    assert (
        await hass.services.async_call(
            DOMAIN,
            "set_schedule",
            {"entity_id": entity, "revision": week.revision, "days": days},
            blocking=True,
        )
        is None
    )
    mock_client.async_send_schedule.assert_not_awaited()


async def test_bundled_card_is_served_by_ha(hass, entry, mock_client, hass_client):
    await schedule_setup(hass, entry, mock_client)
    client = await hass_client()
    response = await client.get("/kdomo/kdomo-schedule-card.js?v=0.4.0")
    assert response.status == 200
    content = await response.text()
    assert 'customElements.define("kdomo-schedule-card"' in content
    assert "test-only-password" not in content


async def test_schedule_optout_during_read_prevents_send(hass, entry, mock_client):
    coordinator, _ = await schedule_setup(hass, entry, mock_client)
    week, days, *_ = edited_week()

    async def fresh_read(_device):
        hass.config_entries.async_update_entry(entry, options={"write_enabled": False})
        return schedule_snapshot()

    mock_client.async_state.side_effect = fresh_read
    with pytest.raises(HomeAssistantError, match="disabled before sending"):
        await coordinator.async_schedule(DEVICE, days=days, revision=week.revision)
    mock_client.async_send_schedule.assert_not_awaited()
