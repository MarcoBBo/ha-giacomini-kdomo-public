"""UI setup, plant selection, reauthentication and options."""

from __future__ import annotations

import hashlib
from typing import Any

try:
    import probatio as vol
except ModuleNotFoundError:  # Home Assistant 2026.2 uses voluptuous.
    import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KdomoClient
from .const import (
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    CONF_POLL_INTERVAL,
    CONF_WRITE_ENABLED,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)
from .models import AuthenticationError, KdomoError, PrivacyError


def entry_unique_id(username: str, plant_id: str) -> str:
    # The cloud has not exposed a verified stable account id. Never put an email
    # in the unique id, and do not case-fold a potentially case-sensitive login.
    account = hashlib.sha256(username.encode()).hexdigest()
    return f"{account}:{plant_id}"


class KdomoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, str] = {}
        self._plants: list[dict[str, Any]] = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            client = KdomoClient(async_get_clientsession(self.hass), username, password)
            try:
                self._plants = await client.async_plants()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except PrivacyError:
                errors["base"] = "privacy_required"
            except KdomoError:
                errors["base"] = "cannot_connect"
            else:
                if not self._plants:
                    return self.async_abort(reason="no_plants")
                self._credentials = {CONF_USERNAME: username, CONF_PASSWORD: password}
                return await self.async_step_plant()
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}),
        )

    async def async_step_plant(self, user_input=None):
        errors = {}
        plants = {p["id"]: p for p in self._plants}
        if user_input is not None:
            plant_id = user_input[CONF_PLANT_ID]
            if plant_id not in plants:
                errors["base"] = "plant_unavailable"
            else:
                await self.async_set_unique_id(entry_unique_id(self._credentials[CONF_USERNAME], plant_id))
                self._abort_if_unique_id_configured()
                plant_name = str(plants[plant_id].get("name") or "K-Domo")
                return self.async_create_entry(
                    title=plant_name,
                    data={**self._credentials, CONF_PLANT_ID: plant_id, CONF_PLANT_NAME: plant_name},
                    options={CONF_WRITE_ENABLED: False, CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL},
                )
        return self.async_show_form(
            step_id="plant",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLANT_ID): vol.In(
                        {p["id"]: str(p.get("name") or "K-Domo") for p in self._plants}
                    )
                }
            ),
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            # Keep the original username and selected plant. Reauth never changes
            # account identity or silently adds another entry.
            client = KdomoClient(
                async_get_clientsession(self.hass),
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                plants = await client.async_plants()
                if not any(p["id"] == entry.data[CONF_PLANT_ID] for p in plants):
                    errors["base"] = "plant_unavailable"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except PrivacyError:
                errors["base"] = "privacy_required"
            except KdomoError:
                errors["base"] = "cannot_connect"
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KdomoOptionsFlow()


class KdomoOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WRITE_ENABLED, default=options.get(CONF_WRITE_ENABLED, False)): bool,
                    vol.Required(
                        CONF_POLL_INTERVAL, default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)),
                }
            ),
        )
