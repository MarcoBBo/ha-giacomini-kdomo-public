from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kdomo.config_flow import entry_unique_id
from custom_components.kdomo.const import DOMAIN
from custom_components.kdomo.models import AuthenticationError, KdomoError, PrivacyError


@pytest.fixture
def flow_client():
    with patch("custom_components.kdomo.config_flow.KdomoClient", autospec=True) as factory:
        client = factory.return_value
        client.async_plants.return_value = [
            {"id": "plant-example", "name": "Example plant", "thermostats": []}
        ]
        yield client


async def test_user_plant_and_readonly_options(hass, flow_client):
    with patch("custom_components.kdomo.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "example@example.invalid",
                "password": "test-only-password",
            },
        )
        assert result["step_id"] == "plant"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"plant_id": "plant-example"}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Example plant"
    assert result["options"] == {"write_enabled": False, "poll_interval": 60}
    assert result["result"].unique_id == entry_unique_id("example@example.invalid", "plant-example")
    flow_client.async_send_settings.assert_not_awaited()


@pytest.mark.parametrize(
    "error,reason",
    [
        (AuthenticationError("Rejected"), "invalid_auth"),
        (PrivacyError("Required"), "privacy_required"),
        (KdomoError("Unavailable"), "cannot_connect"),
    ],
)
async def test_login_errors(hass, flow_client, error, reason):
    flow_client.async_plants.side_effect = error
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            "username": "example@example.invalid",
            "password": "test-only-password",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": reason}


async def test_no_plants(hass, flow_client):
    flow_client.async_plants.return_value = []
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            "username": "example@example.invalid",
            "password": "test-only-password",
        },
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_plants"


async def test_duplicate_plant_rejected(hass, entry, flow_client):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, unique_id=entry_unique_id("example@example.invalid", "plant-example")
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            "username": "example@example.invalid",
            "password": "test-only-password",
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"plant_id": "plant-example"})
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_existing_entry_only(hass, entry, flow_client):
    entry.add_to_hass(hass)
    with patch("homeassistant.config_entries.ConfigEntries.async_reload", return_value=True) as reload:
        result = await entry.start_reauth_flow(hass)
        assert result["step_id"] == "reauth_confirm"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "new-test-password"}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new-test-password"
    assert entry.data["username"] == "example@example.invalid"
    assert entry.data["plant_id"] == "plant-example"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    reload.assert_awaited_once()


async def test_reauth_inaccessible_plant_does_not_update(hass, entry, flow_client):
    entry.add_to_hass(hass)
    flow_client.async_plants.return_value = [{"id": "other-plant"}]
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"password": "new-test-password"}
    )
    assert result["errors"] == {"base": "plant_unavailable"}
    assert entry.data["password"] == "test-only-password"


async def test_options(hass, entry):
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "write_enabled": True,
            "poll_interval": 120,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {"write_enabled": True, "poll_interval": 120, "schedule_write_enabled": False}
