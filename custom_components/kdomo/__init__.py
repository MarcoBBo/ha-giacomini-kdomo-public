"""Independent Giacomini K-Domo cloud integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KdomoClient
from .const import CONF_PLANT_ID, DOMAIN
from .coordinator import KdomoCoordinator
from .models import AuthenticationError, KdomoError, PrivacyError
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = KdomoClient(async_get_clientsession(hass), entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    try:
        devices = await client.async_devices(entry.data[CONF_PLANT_ID])
    except (AuthenticationError, PrivacyError) as err:
        raise ConfigEntryAuthFailed("Check credentials and privacy acceptance in K-Domo") from err
    except KdomoError as err:
        raise ConfigEntryNotReady("Cannot discover the selected K-Domo plant") from err
    coordinator = KdomoCoordinator(hass, entry, client, devices)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
