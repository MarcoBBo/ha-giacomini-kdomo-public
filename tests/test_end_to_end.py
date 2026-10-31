"""HA config flow -> real async HTTP client -> simulated cloud -> HA service."""

import asyncio
import time
from unittest.mock import patch

from aiohttp import web
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kdomo.const import DOMAIN, PRESET_GROUPS, PRESET_TEMPERATURES


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
    values.update(
        {
            f"progDay{day}": f"0;{day};2;06:30;1;09:00;3;18:00;4;23:00;2;23:59;0;23:59;0;23:59;0;23:59"
            for day in range(7)
        }
    )
    commands = []
    topics = []
    values.update(dict.fromkeys(PRESET_TEMPERATURES, "20"))
    values.update({key: "0" for _, integers in PRESET_GROUPS.values() for key in integers})

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
        topic = request.path.rsplit("/", 1)[-1]
        assert topic in ("02", "03", "10", "11")
        assert request.method == "POST"
        body = await request.json()
        commands.append(body)
        topics.append(topic)
        if topic == "03":
            fields = body["completeschedule"].split(";")
            assert len(fields) == 116
            values.update(
                {
                    f"progDay{day}": ";".join([fields[0], str(day)] + fields[4 + day * 16 : 20 + day * 16])
                    for day in range(7)
                }
            )
        else:
            values.update({key: str(value) for key, value in body.items()})
        return web.json_response({"data": {"requesttopic": topic, "expectreply": False}})

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
        hass.config_entries.async_update_entry(
            entry, options={"write_enabled": True, "poll_interval": 60, "schedule_write_enabled": True}
        )
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
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)

        async def set_preset(key, target):
            number_id = registry.async_get_entity_id("number", "kdomo", f"plant-example:serial-example:{key}")
            await hass.services.async_call(
                "number", "set_value", {"entity_id": number_id, "value": target}, blocking=True
            )
            assert float(hass.states.get(number_id).state) == target

        climate_before = {key: values[key] for key in ("mode", "status", "program", "currentsetpoint")}
        with patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0,)):
            # Simultaneous services must preserve each other's changes in the same group.
            await asyncio.gather(
                set_preset("heatingtempcomfort", 23),
                set_preset("heatingtempnight", 18),
            )
            await set_preset("coolingtempcomfortplus", 25)
        assert values["heatingtempcomfort"] == "+23.0"
        assert values["heatingtempnight"] == "+18.0"
        assert {key: values[key] for key in climate_before} == climate_before
        assert topics == ["02", "10", "10", "11"]
        for topic, body in zip(topics[1:], commands[1:], strict=True):
            temperatures, integers = PRESET_GROUPS[topic]
            assert set(body) == set(temperatures + integers)
        data = await hass.services.async_call(
            DOMAIN, "get_schedule", {"entity_id": entity_id}, blocking=True, return_response=True
        )
        original_days = {day: values[f"progDay{day}"] for day in range(7)}
        data["days"][1]["slots"][1]["end"] = 570
        with patch("custom_components.kdomo.coordinator.VERIFY_DELAYS", (0,)):
            confirmed = await hass.services.async_call(
                DOMAIN,
                "set_schedule",
                {"entity_id": entity_id, "revision": data["revision"], "days": data["days"]},
                blocking=True,
                return_response=True,
            )
        assert confirmed["days"][1]["slots"][1]["end"] == 570
        assert topics[-1] == "03" and set(commands[-1]) == {"completeschedule"}
        assert {key: values[key] for key in climate_before} == climate_before
        for day in (0, 2, 3, 4, 5, 6):
            assert values[f"progDay{day}"] == original_days[day]
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert len(commands) == 5
