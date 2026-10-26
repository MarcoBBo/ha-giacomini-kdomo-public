"""Cloud-reported connectivity, available even when the thermostat is offline."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import KdomoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    async_add_entities(KdomoConnectivity(coordinator, device, "online") for device in coordinator.devices)


class KdomoConnectivity(KdomoEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "online"

    @property
    def available(self) -> bool:
        return CoordinatorEntity.available.fget(self) and not self.snapshot.error

    @property
    def is_on(self) -> bool:
        return self.snapshot.online
