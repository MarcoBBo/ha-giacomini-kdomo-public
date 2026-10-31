"""Asynchronous K-Domo cloud client. No redirects, TLS bypass or POST replay."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import BASE_URL, PARAMETERS
from .models import (
    AuthenticationError,
    CommandUncertainError,
    Device,
    KdomoError,
    PrivacyError,
    ProtocolError,
    RateLimitError,
    Snapshot,
    decode_measurements,
)

MAX_RESPONSE_BYTES = 1024 * 1024


def segment(value: str) -> str:
    if not value or value in (".", ".."):
        raise ProtocolError("Invalid cloud resource identifier")
    return quote(value, safe="")


class KdomoClient:
    """One account session; credentials remain private and token stays in memory."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None
        self._login_lock = asyncio.Lock()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json", "Cache-Control": "no-cache", "Pragma": "no-cache"}
        if authenticated:
            if not self._token:
                raise AuthenticationError("Authentication required")
            headers["X-Auth-Token"] = self._token
        url = BASE_URL + path
        if method == "GET":
            url += "?_=" + str(time.time_ns())
        try:
            async with self._session.request(
                method,
                url,
                json=body,
                headers=headers,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (401, 403):
                    raise AuthenticationError("Cloud authentication rejected")
                if response.status == 429:
                    try:
                        retry_after = max(60, min(int(response.headers.get("Retry-After", "60")), 3600))
                    except ValueError:
                        retry_after = 60
                    raise RateLimitError(retry_after)
                if not 200 <= response.status < 300:
                    if method == "POST" and authenticated:
                        raise CommandUncertainError("Command not confirmed; no automatic retry")
                    raise KdomoError(f"Cloud HTTP error {response.status}")
                chunks = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    chunks.extend(chunk)
                    if len(chunks) > MAX_RESPONSE_BYTES:
                        raise ProtocolError("Cloud response exceeds the supported size")
                try:
                    return json.loads(chunks)
                except (ValueError, UnicodeError) as from_error:
                    raise ProtocolError("Unexpected cloud response") from from_error
        except (aiohttp.ClientError, TimeoutError) as err:
            if method == "POST" and authenticated:
                raise CommandUncertainError("Command delivery unknown; no automatic retry") from err
            raise KdomoError("Cloud connection failed") from err

    async def async_login(self) -> None:
        async with self._login_lock:
            await self._async_login_unlocked()

    async def _async_login_unlocked(self) -> None:
        self._token = None
        response = await self._request(
            "POST",
            "auth/v2",
            body={"username": self._username, "password": self._password},
            authenticated=False,
        )
        if (
            not isinstance(response, dict)
            or not isinstance(response.get("token"), str)
            or not response["token"]
        ):
            raise ProtocolError("Login response has no token")
        if response.get("privacyAccepted") is not True:
            raise PrivacyError("Complete privacy acceptance in the official K-Domo app")
        self._token = response["token"]

    async def _get(self, path: str) -> Any:
        if self._token is None:
            await self.async_login()
        failed_token = self._token
        try:
            return await self._request("GET", path)
        except AuthenticationError:
            async with self._login_lock:
                if self._token == failed_token:
                    await self._async_login_unlocked()
            # Exactly one replay, for this read operation only.
            return await self._request("GET", path)

    async def async_plants(self) -> list[dict[str, Any]]:
        response = await self._get("plants")
        if not isinstance(response, dict) or not isinstance(response.get("data"), list):
            raise ProtocolError("Unexpected plant list")
        plants = response["data"]
        if any(not isinstance(p, dict) or not isinstance(p.get("id"), str) for p in plants):
            raise ProtocolError("Invalid plant record")
        return plants

    async def async_devices(self, plant_id: str) -> list[Device]:
        plants = await self.async_plants()
        plant = next((p for p in plants if p["id"] == plant_id), None)
        if plant is None:
            raise ProtocolError("Selected plant is no longer accessible")
        rows = plant.get("thermostats")
        if not isinstance(rows, list):
            raise ProtocolError("Unexpected thermostat list")
        devices = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("serial"), str) or not row["serial"]:
                raise ProtocolError("Invalid thermostat serial")
            if row["serial"] not in seen:
                devices.append(Device(plant_id, row["serial"], str(row.get("name") or "K-Domo")))
                seen.add(row["serial"])
        return devices

    async def async_state(self, device: Device) -> Snapshot:
        path = f"thermostats/{segment(device.plant_id)}/{segment(device.serial)}/"
        rows = await self._get(path + "lasts/parameters/" + ",".join(PARAMETERS))
        online = await self._get(path + "isonline")
        if not isinstance(online, dict) or not isinstance(online.get("data"), bool):
            raise ProtocolError("Unexpected online status")
        return decode_measurements(rows, online=online["data"])

    async def async_send_settings(self, device: Device, payload: dict[str, Any]) -> None:
        """An acknowledgement is not state confirmation."""
        await self._async_send_command(device, "02", payload)

    async def async_send_presets(self, device: Device, topic: str, payload: dict[str, Any]) -> None:
        """Only the two preset-temperature groups are accepted."""
        if topic not in ("10", "11"):
            raise ProtocolError("Unsupported preset command group")
        await self._async_send_command(device, topic, payload)

    async def async_send_schedule(self, device: Device, payload: dict[str, Any]) -> None:
        """Send a complete week once; confirmation is the coordinator's responsibility."""
        await self._async_send_command(device, "03", payload)

    async def _async_send_command(self, device: Device, topic: str, payload: dict[str, Any]) -> None:
        path = f"thermostats/{segment(device.plant_id)}/{segment(device.serial)}/sendCommand/{topic}"
        response = await self._request("POST", path, body=payload)
        if not isinstance(response, dict) or not isinstance(response.get("data"), dict):
            raise CommandUncertainError("Command acknowledgement is invalid; delivery unknown")
