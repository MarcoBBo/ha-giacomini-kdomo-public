"""Real aiohttp traffic to a loopback-only synthetic cloud; never the vendor."""

from collections import deque
from unittest.mock import patch

import aiohttp
import pytest
from aiohttp import web

from custom_components.kdomo.api import MAX_RESPONSE_BYTES, KdomoClient, segment
from custom_components.kdomo.models import (
    AuthenticationError,
    CommandUncertainError,
    KdomoError,
    PrivacyError,
    ProtocolError,
    RateLimitError,
)

from .conftest import DEVICE


class Cloud:
    def __init__(self):
        self.queue = deque()
        self.calls = []

    def response(self, status=200, *, payload=None, body=None, headers=None):
        self.queue.append((status, payload, body, headers))

    async def handle(self, request):
        self.calls.append(
            {
                "method": request.method,
                "path": request.path,
                "query": dict(request.query),
                "headers": dict(request.headers),
                "body": await request.json() if request.can_read_body else None,
            }
        )
        if not self.queue:
            return web.Response(status=500)
        status, payload, body, headers = self.queue.popleft()
        if body is not None:
            return web.Response(status=status, text=body, headers=headers)
        return web.json_response(payload, status=status, headers=headers)


@pytest.fixture
async def api(aiohttp_server, socket_enabled):
    cloud = Cloud()
    app = web.Application()
    app.router.add_route("*", "/{path:.*}", cloud.handle)
    server = await aiohttp_server(app, host="127.0.0.1")
    async with aiohttp.ClientSession() as session:
        with patch("custom_components.kdomo.api.BASE_URL", str(server.make_url("/"))):
            yield KdomoClient(session, "example@example.invalid", "test-only-password"), cloud


async def test_login_and_header_no_bearer(api):
    client, cloud = api
    cloud.response(payload={"token": "synthetic-token", "privacyAccepted": True})
    cloud.response(payload={"data": []})
    assert await client.async_plants() == []
    login, read = cloud.calls
    assert login["body"] == {"username": "example@example.invalid", "password": "test-only-password"}
    assert "X-Auth-Token" not in login["headers"]
    assert read["headers"]["X-Auth-Token"] == "synthetic-token"
    assert "Authorization" not in read["headers"]
    assert read["headers"]["Cache-Control"] == "no-cache"
    assert read["query"]["_"].isdigit()


async def test_read_reauth_once(api):
    client, cloud = api
    client._token = "expired"
    cloud.response(401)
    cloud.response(payload={"token": "renewed", "privacyAccepted": True})
    cloud.response(payload={"data": []})
    assert await client.async_plants() == []
    assert [c["method"] for c in cloud.calls] == ["GET", "POST", "GET"]


async def test_read_does_not_loop_on_rejected_relogin(api):
    client, cloud = api
    client._token = "expired"
    cloud.response(401)
    cloud.response(401)
    with pytest.raises(AuthenticationError):
        await client.async_plants()
    assert len(cloud.calls) == 2


@pytest.mark.parametrize("privacy", [False, None])
async def test_privacy_never_silently_accepted(api, privacy):
    client, cloud = api
    cloud.response(payload={"token": "synthetic-token", "privacyAccepted": privacy})
    with pytest.raises(PrivacyError):
        await client.async_login()
    assert client._token is None


async def test_no_redirect_following(api):
    client, cloud = api
    cloud.response(302, headers={"Location": "/steal"})
    with pytest.raises(KdomoError):
        await client.async_login()
    assert len(cloud.calls) == 1


async def test_authenticated_redirect_does_not_forward_token(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(302, headers={"Location": "/steal"})
    with pytest.raises(KdomoError):
        await client.async_plants()
    assert len(cloud.calls) == 1
    assert cloud.calls[0]["path"] == "/plants"


@pytest.mark.parametrize(
    "status,error",
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (500, CommandUncertainError),
        (429, RateLimitError),
    ],
)
async def test_commands_never_replayed(api, status, error):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(status)
    with pytest.raises(error):
        await client.async_send_settings(DEVICE, {})
    assert len(cloud.calls) == 1


async def test_timeout_is_uncertain_and_not_retried(api):
    client, _ = api
    client._token = "synthetic-token"
    with patch.object(client._session, "request", side_effect=TimeoutError) as request:
        with pytest.raises(CommandUncertainError):
            await client.async_send_settings(DEVICE, {})
    request.assert_called_once()


async def test_rate_limit_and_no_server_body_leak(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(429, headers={"Retry-After": "180"}, body="private server body")
    with pytest.raises(RateLimitError) as exc:
        await client.async_plants()
    assert exc.value.retry_after == 180
    assert "private" not in str(exc.value)


async def test_malformed_response(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(body="not json")
    with pytest.raises(ProtocolError):
        await client.async_plants()


async def test_oversized_response(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(body="a" * (MAX_RESPONSE_BYTES + 1))
    with pytest.raises(ProtocolError):
        await client.async_plants()


async def test_device_selection_uses_serial_and_selected_plant(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(
        payload={
            "data": [
                {"id": "another-plant", "thermostats": [{"serial": "another-serial"}]},
                {
                    "id": "plant-example",
                    "thermostats": [
                        {"id": "internal-id", "serial": "serial-example", "name": "Example thermostat"}
                    ],
                },
            ]
        }
    )
    assert await client.async_devices("plant-example") == [DEVICE]


async def test_typed_state_read(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(payload=[{"parameter": "temperature", "when": 1000, "doubleVal": 20.4}])
    cloud.response(payload={"data": True})
    state = await client.async_state(DEVICE)
    assert state.online and state.number("temperature") == 20.4
    assert cloud.calls[0]["path"].startswith("/thermostats/plant-example/serial-example/lasts/parameters/")


async def test_command_wire_body_and_ack(api):
    client, cloud = api
    client._token = "synthetic-token"
    cloud.response(payload={"data": {"requesttopic": "02", "expectreply": False}})
    body = {"mode": 2, "program": 0, "status": 1, "currentsetpoint": "+22.0", "fancoil": "0"}
    await client.async_send_settings(DEVICE, body)
    assert cloud.calls[0]["path"].endswith("/sendCommand/02")
    assert cloud.calls[0]["body"] == body


def test_path_segments():
    assert segment("abc/xyz") == "abc%2Fxyz"
    with pytest.raises(ProtocolError):
        segment("..")


@pytest.mark.parametrize("topic", ["10", "11"])
async def test_preset_wire_and_rejection_never_replayed(api, topic):
    client, cloud = api
    client._token = "synthetic-token"
    body = {"heatingtempcomfort" if topic == "10" else "coolingtempcomfort": "+22.0"}
    cloud.response(payload={"data": {"requesttopic": topic}})
    await client.async_send_presets(DEVICE, topic, body)
    assert cloud.calls[0]["path"].endswith("/sendCommand/" + topic)
    assert cloud.calls[0]["body"] == body
    cloud.response(401)
    with pytest.raises(AuthenticationError):
        await client.async_send_presets(DEVICE, topic, body)
    assert len(cloud.calls) == 2


async def test_preset_invalid_topic_never_sent(api):
    client, cloud = api
    with pytest.raises(ProtocolError):
        await client.async_send_presets(DEVICE, "03", {})
    assert not cloud.calls
