from unittest.mock import patch

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kdomo.climate import KdomoClimate
from custom_components.kdomo.diagnostics import async_get_config_entry_diagnostics
from custom_components.kdomo.models import AuthenticationError, KdomoError, RateLimitError

from .conftest import DEVICE, snapshot


async def setup(hass, entry):
    if hass.config_entries.async_get_entry(entry.entry_id) is None:
        entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def test_setup_all_entities_no_writes_and_unload(hass, entry, mock_client):
    coordinator = await setup(hass, entry)
    states = hass.states.async_all()
    own = [s for s in states if s.entity_id.startswith(("climate.", "sensor.", "binary_sensor."))]
    assert len(own) == 4
    climate = next(s for s in own if s.domain == "climate")
    assert climate.state == "off"
    assert climate.attributes["temperature"] == 21
    assert climate.attributes["current_temperature"] == 20.4
    assert climate.attributes["current_humidity"] == 55
    mock_client.async_send_settings.assert_not_awaited()
    assert coordinator.update_interval.total_seconds() == 60
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    mock_client.async_send_settings.assert_not_awaited()


async def test_controls_disabled_default(hass, entry, mock_client):
    coordinator = await setup(hass, entry)
    with pytest.raises(HomeAssistantError, match="disabled"):
        await coordinator.async_command(DEVICE, target=22)
    mock_client.async_send_settings.assert_not_awaited()


async def test_command_verified_and_preserves_group(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True, "poll_interval": 60})
    coordinator = await setup(hass, entry)
    mock_client.async_state.side_effect = [
        snapshot(),
        snapshot(mode=2, status=1, currentsetpoint=22, when=1003),
    ]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch(
            "custom_components.kdomo.coordinator.VERIFY_DELAYS",
            (0,),
        ),
    ):
        await coordinator.async_command(DEVICE, target=22, operation="heat")
    mock_client.async_send_settings.assert_awaited_once_with(
        DEVICE,
        {"mode": 2, "program": 0, "status": 1, "currentsetpoint": "+22.0", "fancoil": "0"},
    )
    assert coordinator.data[DEVICE.key].number("currentsetpoint") == 22


async def test_ack_without_actual_change_raises_and_no_rollback(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    coordinator = await setup(hass, entry)
    with patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0, 0)):
        with pytest.raises(HomeAssistantError, match="not confirmed"):
            await coordinator.async_command(DEVICE, target=22, operation="heat")
    mock_client.async_send_settings.assert_awaited_once()
    assert coordinator.data[DEVICE.key].number("currentsetpoint") == 21


async def test_noop_sends_nothing(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    coordinator = await setup(hass, entry)
    await coordinator.async_command(DEVICE, operation="off")
    mock_client.async_send_settings.assert_not_awaited()


async def test_diagnostics_whitelist(hass, entry, mock_client):
    await setup(hass, entry)
    result = await async_get_config_entry_diagnostics(hass, entry)
    text = str(result)
    for private in (
        "test-only-password",
        "example@example.invalid",
        "plant-example",
        "serial-example",
        "Example thermostat",
        "Example plant",
    ):
        assert private not in text


async def test_offline_thermostat_has_connection_off(hass, entry, mock_client):
    mock_client.async_state.return_value = snapshot(online=False)
    await setup(hass, entry)
    assert next(s for s in hass.states.async_all() if s.domain == "climate").state == "unavailable"
    assert next(s for s in hass.states.async_all() if s.domain == "binary_sensor").state == "off"


async def test_poll_auth_failure_starts_reauth(hass, entry, mock_client):
    coordinator = await setup(hass, entry)
    mock_client.async_state.side_effect = AuthenticationError("Rejected")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_poll_rate_limit_backoff(hass, entry, mock_client):
    coordinator = await setup(hass, entry)
    mock_client.async_state.side_effect = RateLimitError(180)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    calls = mock_client.async_state.await_count
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert mock_client.async_state.await_count == calls


async def test_device_read_failure_isolated(hass, entry, mock_client):
    coordinator = await setup(hass, entry)
    second = type(DEVICE)(DEVICE.plant_id, "serial-second", "Second device")
    coordinator.devices.append(second)
    mock_client.async_state.side_effect = [KdomoError("Read failed"), snapshot()]
    data = await coordinator._async_update_data()
    assert data[DEVICE.key].error
    assert not data[second.key].error


async def test_mode_mapping_and_never_guess_relay_activity(hass, entry, mock_client):
    coordinator = await setup(hass, entry)
    entity = KdomoClimate(coordinator, DEVICE, "climate")
    assert entity.hvac_mode == HVACMode.OFF
    for changes, expected in [
        ({"mode": 1, "status": 1}, HVACMode.AUTO),
        ({"mode": 2, "status": 1}, HVACMode.HEAT),
        ({"mode": 0, "status": 1}, HVACMode.HEAT),
        ({"program": 1, "mode": 2, "status": 1}, HVACMode.COOL),
        ({"status": 2}, None),
    ]:
        coordinator.async_set_updated_data({DEVICE.key: snapshot(**changes)})
        assert entity.hvac_mode == expected
    assert entity.hvac_action is None


async def test_service_temperature_reaches_verified_command(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    await setup(hass, entry)
    entity_id = next(s.entity_id for s in hass.states.async_all() if s.domain == "climate")
    mock_client.async_state.side_effect = [snapshot(), snapshot(mode=2, currentsetpoint=22, when=1003)]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch(
            "custom_components.kdomo.coordinator.VERIFY_DELAYS",
            (0,),
        ),
    ):
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": entity_id, ATTR_TEMPERATURE: 22},
            blocking=True,
        )
    assert hass.states.get(entity_id).attributes["temperature"] == 22
    assert hass.states.get(entity_id).state == "off"  # Target alone does not turn it on.


async def test_fahrenheit_device_uses_ha_conversion(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    before = snapshot(scale=1, temperature=68, currentsetpoint=69.8)
    mock_client.async_state.return_value = before
    await setup(hass, entry)
    entity_id = next(s.entity_id for s in hass.states.async_all() if s.domain == "climate")
    assert hass.states.get(entity_id).attributes["current_temperature"] == 20
    mock_client.async_state.side_effect = [
        before,
        snapshot(scale=1, temperature=68, currentsetpoint=71.6, mode=2, when=1003),
    ]
    with (
        patch("custom_components.kdomo.coordinator.time.time", return_value=1002),
        patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0,)),
    ):
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": entity_id, ATTR_TEMPERATURE: 22},
            blocking=True,
        )
    assert mock_client.async_send_settings.call_args.args[1]["currentsetpoint"] == "+71.6"
    assert hass.states.get(entity_id).attributes["temperature"] == 22


async def test_command_offline_never_sent(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    coordinator = await setup(hass, entry)
    mock_client.async_state.return_value = snapshot(online=False)
    with pytest.raises(HomeAssistantError, match="unavailable"):
        await coordinator.async_command(DEVICE, target=22)
    mock_client.async_send_settings.assert_not_awaited()


async def test_command_auth_error_triggers_reauth_without_replay(hass, entry, mock_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"write_enabled": True})
    coordinator = await setup(hass, entry)
    mock_client.async_send_settings.side_effect = AuthenticationError("Rejected")
    with patch.object(type(entry), "async_start_reauth") as reauth:
        with pytest.raises(HomeAssistantError, match="authentication"):
            await coordinator.async_command(DEVICE, target=22)
    reauth.assert_called_once_with(hass)
    mock_client.async_send_settings.assert_awaited_once()
