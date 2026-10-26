from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kdomo.const import DOMAIN
from custom_components.kdomo.models import Device, Snapshot

DEVICE = Device("plant-example", "serial-example", "Example thermostat")


def snapshot(*, online=True, when=1000, **changes):
    values = {
        "name": "Example thermostat",
        "temperature": "20.4",
        "humidity": "55",
        "mode": "1",
        "program": "0",
        "status": "0",
        "currentsetpoint": "21",
        "fancoil": "0",
        "scale": "0",
        "prog0": "0;Winter;0;0",
        "prog1": "1;Summer;1;0",
    }
    values.update({key: str(value) for key, value in changes.items()})
    return Snapshot(values, dict.fromkeys(values, when), online)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def entry():
    return MockConfigEntry(
        domain=DOMAIN,
        title="Example plant",
        unique_id="example-account:plant-example",
        data={
            "username": "example@example.invalid",
            "password": "test-only-password",
            "plant_id": "plant-example",
            "plant_name": "Example plant",
        },
        options={"write_enabled": False, "poll_interval": 60},
    )


@pytest.fixture
def mock_client():
    with patch("custom_components.kdomo.KdomoClient", autospec=True) as factory:
        client = factory.return_value
        client.async_devices = AsyncMock(return_value=[DEVICE])
        client.async_state = AsyncMock(return_value=snapshot())
        client.async_send_settings = AsyncMock()
        yield client
