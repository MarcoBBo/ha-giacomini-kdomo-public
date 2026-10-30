"""Preset groups, actual HA number services and synthetic HTTP transport."""

from unittest.mock import patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.kdomo.const import PRESET_GROUPS, PRESET_TEMPERATURES
from custom_components.kdomo.models import ProtocolError, Snapshot, preset_payload

from .conftest import DEVICE, snapshot
from .test_integration import setup


def presets(*, when=1000, **changes):
    values = dict.fromkeys(PRESET_TEMPERATURES, "20")
    values.update({key: "0" for _, integers in PRESET_GROUPS.values() for key in integers})
    values.update(changes)
    return snapshot(when=when, **values)


@pytest.mark.parametrize("key", PRESET_TEMPERATURES)
def test_complete_group_changes_only_requested_temperature(key):
    before = presets(heatingtype=3, heatinggeoinhome=4, coolingtype=2)
    topic, body = preset_payload(before, key, 22.5)
    temperatures, integers = PRESET_GROUPS[topic]
    assert set(body) == set(temperatures + integers)
    assert body[key] == "+22.5"
    for other in temperatures:
        if other != key:
            assert float(body[other]) == before.number(other)
    for other in integers:
        assert body[other] == before.integer(other)
    assert not {"mode", "status", "program", "currentsetpoint", "completeschedule"} & body.keys()


@pytest.mark.parametrize("key", PRESET_TEMPERATURES + ("heatinggeoinhome", "coolingtype"))
def test_missing_group_member_is_not_defaulted(key):
    before = presets()
    values = dict(before.values)
    del values[key]
    state = Snapshot(values, before.timestamps, True)
    target = "coolingtempcomfort" if key.startswith("cooling") else "heatingtempcomfort"
    with pytest.raises(ProtocolError, match="Incomplete"):
        preset_payload(state, target, 22)


@pytest.mark.parametrize(
    "changes",
    [
        {"scale": 9},
        {"heatingtype": "bad"},
        {"heatingtype": 1.5},
        {"heatingtype": 2**31},
        {"heatingtempnight": "nan"},
        {"heatingtempnight": "20.25"},
        {"heatingtempnight": 40},
    ],
)
def test_invalid_preserved_fields_block_write(changes):
    with pytest.raises(ProtocolError):
        preset_payload(presets(**changes), "heatingtempcomfort", 22)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 36, True, "bad"])
def test_invalid_requested_temperature(value):
    with pytest.raises(ProtocolError):
        preset_payload(presets(), "heatingtempcomfort", value)


def test_unknown_preset_offline_and_fahrenheit():
    with pytest.raises(ProtocolError, match="Unsupported preset"):
        preset_payload(presets(), "currentsetpoint", 22)
    with pytest.raises(ProtocolError, match="unavailable"):
        preset_payload(presets(online=False), "heatingtempcomfort", 22)
    temperatures = dict.fromkeys(PRESET_TEMPERATURES, 68)
    topic, body = preset_payload(presets(scale=1, **temperatures), "coolingtempnight", 71.6)
    assert topic == "11" and body["coolingtempnight"] == "+71.6"


async def test_number_setup_readonly_missing_and_updates(hass, entry, mock_client):
    mock_client.async_state.return_value = presets()
    coordinator = await setup(hass, entry)
    numbers = [s for s in hass.states.async_all() if s.domain == "number"]
    assert len(numbers) == 10
    assert all(float(s.state) == 20 for s in numbers)
    assert all(s.attributes["unit_of_measurement"] == "°C" for s in numbers)
    assert all(s.attributes["step"] == 0.5 for s in numbers)
    mock_client.async_send_presets.assert_not_awaited()
    with pytest.raises(HomeAssistantError, match="disabled"):
        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": numbers[0].entity_id,
                "value": 22,
            },
            blocking=True,
        )
    coordinator.async_set_updated_data({DEVICE.key: snapshot()})
    assert all(hass.states.get(s.entity_id).state == "unavailable" for s in numbers)
    coordinator.async_set_updated_data({DEVICE.key: presets(scale=9)})
    assert all(hass.states.get(s.entity_id).state == "unavailable" for s in numbers)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    mock_client.async_send_presets.assert_not_awaited()


@pytest.mark.parametrize("key", PRESET_TEMPERATURES)
async def test_ha_number_service_verifies_each_temperature(hass, entry, mock_client, key):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    mock_client.async_state.return_value = presets()
    await setup(hass, entry)
    from homeassistant.helpers import entity_registry as er

    entity_id = er.async_get(hass).async_get_entity_id("number", "kdomo", f"{DEVICE.key}:{key}")
    mock_client.async_state.side_effect = [
        presets(heatingtype=3),
        presets(when=1003, heatingtype=3, **{key: 22}),
    ]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch(
            "custom_components.kdomo.coordinator.VERIFY_DELAYS",
            (0,),
        ),
    ):
        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": entity_id,
                "value": 22,
            },
            blocking=True,
        )
    topic, body = preset_payload(presets(heatingtype=3), key, 22)
    mock_client.async_send_presets.assert_awaited_once_with(DEVICE, topic, body)
    mock_client.async_send_settings.assert_not_awaited()
    assert float(hass.states.get(entity_id).state) == 22


@pytest.mark.parametrize("failure", ["unchanged", "stale", "partial", "scale"])
async def test_unconfirmed_preset_no_replay_no_optimistic_state(hass, entry, mock_client, failure):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    mock_client.async_state.return_value = presets()
    coordinator = await setup(hass, entry)
    after = presets(when=1003, heatingtempcomfort=22)
    if failure == "unchanged":
        after = presets(when=1003)
    elif failure == "stale":
        after = presets(heatingtempcomfort=22)
    elif failure == "partial":
        after = presets(when=1003, heatingtempcomfort=22, heatingtempnight=19)
    else:
        after = presets(when=1003, heatingtempcomfort=22, scale=1)
    mock_client.async_state.side_effect = [presets(), after]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch(
            "custom_components.kdomo.coordinator.VERIFY_DELAYS",
            (0,),
        ),
    ):
        with pytest.raises(HomeAssistantError, match="not confirmed"):
            await coordinator.async_command(DEVICE, preset="heatingtempcomfort", target=22, expected_scale=0)
    assert coordinator.data[DEVICE.key] == after
    mock_client.async_send_presets.assert_awaited_once()
    mock_client.async_send_settings.assert_not_awaited()


async def test_noop_scale_race_and_incomplete_group(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    mock_client.async_state.return_value = presets()
    coordinator = await setup(hass, entry)
    await coordinator.async_command(DEVICE, preset="heatingtempcomfort", target=20, expected_scale=0)
    with pytest.raises(HomeAssistantError, match="scale changed"):
        await coordinator.async_command(DEVICE, preset="heatingtempcomfort", target=22, expected_scale=1)
    mock_client.async_state.return_value = snapshot(heatingtempcomfort=20)
    with pytest.raises(HomeAssistantError, match="Incomplete"):
        await coordinator.async_command(DEVICE, preset="heatingtempcomfort", target=22, expected_scale=0)
    mock_client.async_send_presets.assert_not_awaited()


async def test_number_fahrenheit_service_converts_from_ha_celsius(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    values = dict.fromkeys(PRESET_TEMPERATURES, 68)
    before = presets(scale=1, **values)
    mock_client.async_state.return_value = before
    await setup(hass, entry)
    from homeassistant.helpers import entity_registry as er

    key = "heatingtempcomfort"
    entity_id = er.async_get(hass).async_get_entity_id("number", "kdomo", f"{DEVICE.key}:{key}")
    assert float(hass.states.get(entity_id).state) == 20
    values[key] = 71.6
    mock_client.async_state.side_effect = [before, presets(scale=1, when=1003, **values)]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch(
            "custom_components.kdomo.coordinator.VERIFY_DELAYS",
            (0,),
        ),
    ):
        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": entity_id,
                "value": 22,
            },
            blocking=True,
        )
    assert mock_client.async_send_presets.call_args.args[2][key] == "+71.6"
    assert float(hass.states.get(entity_id).state) == 22
