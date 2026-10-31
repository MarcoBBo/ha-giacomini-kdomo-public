"""Authenticated HA actions for schedules; entity permissions are enforced explicitly."""

from __future__ import annotations

from pathlib import Path

try:
    import probatio as vol
except ModuleNotFoundError:
    import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_CONTROL, POLICY_READ
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import KdomoCoordinator


async def async_setup_services(hass) -> None:
    """Register once per HA lifetime. Static JavaScript contains no private data."""
    if hass.services.has_service(DOMAIN, "get_schedule"):
        return
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/kdomo/kdomo-schedule-card.js",
                str(Path(__file__).parent / "frontend" / "kdomo-schedule-card.js"),
                False,
            )
        ]
    )

    async def handle(call: ServiceCall):
        entity_id = call.data["entity_id"]
        write = call.service == "set_schedule"
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.permissions.check_entity(
                entity_id, POLICY_CONTROL if write else POLICY_READ
            ):
                raise Unauthorized(context=call.context, entity_id=entity_id)
        entity = er.async_get(hass).async_get(entity_id)
        entry = hass.config_entries.async_get_entry(entity.config_entry_id) if entity else None
        coordinator = getattr(entry, "runtime_data", None) if entry else None
        if (
            not entity
            or entity.platform != DOMAIN
            or entity.domain != "climate"
            or not isinstance(coordinator, KdomoCoordinator)
            or entry.state != ConfigEntryState.LOADED
        ):
            raise HomeAssistantError("Select a loaded K-Domo climate entity")
        device = next((d for d in coordinator.devices if entity.unique_id == f"{d.key}:climate"), None)
        if device is None or not hass.states.get(entity_id):
            raise HomeAssistantError("K-Domo thermostat is not loaded")
        result = await coordinator.async_schedule(
            device,
            days=call.data.get("days") if write else None,
            revision=call.data.get("revision") if write else None,
        )
        return result if call.return_response else None

    schema = {vol.Required("entity_id"): cv.entity_id}
    hass.services.async_register(
        DOMAIN, "get_schedule", handle, schema=vol.Schema(schema), supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(
        DOMAIN,
        "set_schedule",
        handle,
        schema=vol.Schema(
            {
                **schema,
                vol.Required("revision"): vol.All(str, vol.Match(r"^[a-f0-9]{64}$")),
                vol.Required("days"): vol.All(list, vol.Length(min=7, max=7)),
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
