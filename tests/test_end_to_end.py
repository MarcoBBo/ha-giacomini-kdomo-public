"""HA config flow -> real async HTTP client -> simulated cloud -> HA service."""

import time
from unittest.mock import patch

from aiohttp import web
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kdomo.const import DOMAIN


async def test_complete_offline_path(hass, aiohttp_server, socket_enabled):
    values = {
        "mode": "1",
        "status": "0",
        "program": "0",
        "currentsetpoint": "21",
        "temperature": "20.4",
        "humidity": "55",
        "fancoil": "0",
        "scale": "0",
        "prog0": "0;Winter;0;0",
    }
    commands = []

    async def handle(request):
        if request.path == "/auth/v2":
            return web.json_response({"token": "synthetic-token", "privacyAccepted": True})
        assert request.headers["X-Auth-Token"] == "synthetic-token"
        if request.path == "/plants":
            return web.json_response(
                {
                    "data": [
                        {
                            "id": "plant-example",
                            "name": "Example plant",
                            "thermostats": [
                                {
                                    "id": "different-internal-id",
                                    "serial": "serial-example",
                                    "name": "Example room",
                                }
                            ],
                        }
                    ]
                }
            )
        if "/lasts/parameters/" in request.path:
            return web.json_response(
                [
                    {"parameter": key, "when": int(time.time()), "stringVal": value}
                    for key, value in values.items()
                ]
            )
        if request.path.endswith("/isonline"):
            return web.json_response({"data": True})
        assert request.path.endswith("/sendCommand/02")
        assert request.method == "POST"
        body = await request.json()
        commands.append(body)
        values.update({key: str(value) for key, value in body.items()})
        return web.json_response({"data": {"requesttopic": "02", "expectreply": False}})

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handle)
    server = await aiohttp_server(app, host="127.0.0.1")
    with patch("custom_components.kdomo.api.BASE_URL", str(server.make_url("/"))):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "username": "example@example.invalid",
                "password": "test-only-password",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"plant_id": "plant-example"}
        )
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.CREATE_ENTRY
        entry = result["result"]
        assert not commands  # Setup and discovery are read only.
        hass.config_entries.async_update_entry(entry, options={"write_enabled": True, "poll_interval": 60})
        await hass.async_block_till_done()
        entity_id = next(s.entity_id for s in hass.states.async_all() if s.domain == "climate")
        with patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0,)):
            await hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": entity_id,
                    "hvac_mode": "heat",
                    "temperature": 22,
                },
                blocking=True,
            )
        assert len(commands) == 1
        assert commands[0] == {
            "mode": 2,
            "program": 0,
            "status": 1,
            "currentsetpoint": "+22.0",
            "fancoil": "0",
        }
        assert hass.states.get(entity_id).state == "heat"
        assert hass.states.get(entity_id).attributes["temperature"] == 22
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert len(commands) == 1
