"""Temperature and humidity sensors."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from .entity import KdomoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        KdomoSensor(coordinator, device, key)
        for device in coordinator.devices
        for key in ("temperature", "humidity")
    )


class KdomoSensor(KdomoEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, device, key: str) -> None:
        super().__init__(coordinator, device, key)
        self.key = key
        self._attr_translation_key = key
        self._attr_device_class = (
            SensorDeviceClass.TEMPERATURE if key == "temperature" else SensorDeviceClass.HUMIDITY
        )

    @property
    def available(self) -> bool:
        return super().available and (self.key != "temperature" or self.snapshot.scale in (0, 1))

    @property
    def native_value(self) -> float | None:
        value = self.snapshot.number(self.key)
        if self.key == "humidity" and value is not None and not 0 <= value <= 100:
            return None
        return value

    @property
    def native_unit_of_measurement(self) -> str:
        if self.key == "humidity":
            return PERCENTAGE
        return UnitOfTemperature.FAHRENHEIT if self.snapshot.scale == 1 else UnitOfTemperature.CELSIUS
