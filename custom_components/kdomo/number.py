"""Native number controls for all documented K-Domo temperature presets."""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature

from .const import PRESET_TEMPERATURES
from .entity import KdomoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        KdomoPresetTemperature(coordinator, device, key)
        for device in coordinator.devices
        for key in PRESET_TEMPERATURES
    )


class KdomoPresetTemperature(KdomoEntity, NumberEntity):
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 0.5

    def __init__(self, coordinator, device, key: str) -> None:
        super().__init__(coordinator, device, key)
        self.key = key
        self._attr_translation_key = key

    @property
    def available(self) -> bool:
        return (
            super().available and self.snapshot.scale in (0, 1) and self.snapshot.number(self.key) is not None
        )

    @property
    def native_value(self) -> float | None:
        return self.snapshot.number(self.key)

    @property
    def native_unit_of_measurement(self) -> str:
        return UnitOfTemperature.FAHRENHEIT if self.snapshot.scale == 1 else UnitOfTemperature.CELSIUS

    @property
    def native_min_value(self) -> float:
        return 32 if self.snapshot.scale == 1 else 0

    @property
    def native_max_value(self) -> float:
        return 95 if self.snapshot.scale == 1 else 35

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_command(
            self.device, preset=self.key, target=value, expected_scale=self.snapshot.scale
        )
