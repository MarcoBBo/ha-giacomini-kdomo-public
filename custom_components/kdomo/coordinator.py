"""Shared polling and serialized, verified commands."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import replace
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KdomoClient
from .const import CONF_POLL_INTERVAL, CONF_WRITE_ENABLED, DEFAULT_POLL_INTERVAL, DOMAIN
from .models import (
    AuthenticationError,
    Device,
    KdomoError,
    PrivacyError,
    RateLimitError,
    Snapshot,
    VerificationError,
    fresh_confirmation,
    settings_payload,
    values_match,
)

_LOGGER = logging.getLogger(__name__)
VERIFY_DELAYS = (2, 5, 10, 10)


class KdomoCoordinator(DataUpdateCoordinator[dict[str, Snapshot]]):
    """One selected plant per config entry; no commands at setup or unload."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: KdomoClient,
        devices: list[Device],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)),
            always_update=False,
        )
        self.client = client
        self.devices = devices
        self.entry = entry
        self._io_lock = asyncio.Lock()
        self._next_request_at = 0.0

    def _enforce_backoff(self) -> None:
        if self._next_request_at > time.monotonic():
            raise RateLimitError(int(self._next_request_at - time.monotonic()) + 1)

    def _set_backoff(self, error: RateLimitError) -> None:
        self._next_request_at = time.monotonic() + error.retry_after

    async def _async_update_data(self) -> dict[str, Snapshot]:
        async with self._io_lock:
            try:
                self._enforce_backoff()
                result = {}
                failures = 0
                for device in self.devices:
                    try:
                        result[device.key] = await self.client.async_state(device)
                    except (AuthenticationError, PrivacyError, RateLimitError):
                        raise
                    except KdomoError:
                        failures += 1
                        previous = (self.data or {}).get(device.key, Snapshot())
                        result[device.key] = replace(previous, online=False, error=True)
                if self.devices and failures == len(self.devices):
                    raise UpdateFailed("K-Domo cloud could not read any thermostat")
                return result
            except (AuthenticationError, PrivacyError) as err:
                raise ConfigEntryAuthFailed(
                    "Sign in again; check privacy acceptance in the official app"
                ) from err
            except RateLimitError as err:
                self._set_backoff(err)
                raise UpdateFailed("K-Domo cloud rate limit; polling paused") from err

    def _publish(self, device: Device, state: Snapshot) -> None:
        self.async_set_updated_data({**(self.data or {}), device.key: state})

    async def async_command(
        self,
        device: Device,
        *,
        target: Any = None,
        operation: str | None = None,
    ) -> None:
        """Read/modify/write, then read back. No optimistic state or rollback."""
        if not self.entry.options.get(CONF_WRITE_ENABLED, False):
            raise HomeAssistantError("K-Domo controls are disabled. Enable them in integration options.")
        async with self._io_lock:
            try:
                self._enforce_backoff()
                before = await self.client.async_state(device)
                self._publish(device, before)
                payload = settings_payload(before, target=target, operation=operation)
                if values_match(before, payload):
                    return
                sent_at = time.time()
                await self.client.async_send_settings(device, payload)
                for delay in VERIFY_DELAYS:
                    await asyncio.sleep(delay)
                    state = await self.client.async_state(device)
                    self._publish(device, state)
                    if fresh_confirmation(before, state, payload, sent_at):
                        return
                raise VerificationError(
                    "Requested state was not confirmed. Check K-Domo before trying again."
                )
            except (AuthenticationError, PrivacyError) as err:
                self.entry.async_start_reauth(self.hass)
                raise HomeAssistantError("K-Domo authentication failed; sign in again") from err
            except RateLimitError as err:
                self._set_backoff(err)
                raise HomeAssistantError("K-Domo rate limit; wait before trying again") from err
            except KdomoError as err:
                # Only sanitized domain exceptions are presented to the user.
                raise HomeAssistantError(str(err)) from err
