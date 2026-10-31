"""Climate controls for the currently selected heating/cooling program."""

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .entity import KdomoEntity
from .models import ProtocolError
from .schedule import decode_week

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    async_add_entities(KdomoClimate(coordinator, device, "climate") for device in coordinator.devices)


class KdomoClimate(KdomoEntity, ClimateEntity):
    _attr_name = None
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )

    @property
    def available(self) -> bool:
        return super().available and self.snapshot.scale in (0, 1)

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.FAHRENHEIT if self.snapshot.scale == 1 else UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float | None:
        return self.snapshot.number("temperature")

    @property
    def current_humidity(self) -> float | None:
        value = self.snapshot.number("humidity")
        return value if value is not None and 0 <= value <= 100 else None

    @property
    def target_temperature(self) -> float | None:
        return self.snapshot.number("currentsetpoint")

    @property
    def min_temp(self) -> float:
        return 32.0 if self.snapshot.scale == 1 else 0.0

    @property
    def max_temp(self) -> float:
        return 95.0 if self.snapshot.scale == 1 else 35.0

    @property
    def hvac_modes(self) -> list[HVACMode]:
        modes = [HVACMode.OFF, HVACMode.AUTO]
        if self.snapshot.season == "heat":
            modes.append(HVACMode.HEAT)
        elif self.snapshot.season == "cool":
            modes.append(HVACMode.COOL)
        return modes

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self.snapshot.integer("status") == 0:
            return HVACMode.OFF
        if self.snapshot.integer("status") != 1:
            return None  # Antifreeze is a distinct K-Domo state, not relay activity.
        if self.snapshot.integer("mode") == 1:
            return HVACMode.AUTO
        if self.snapshot.integer("mode") not in (0, 2):
            return None
        return {"heat": HVACMode.HEAT, "cool": HVACMode.COOL}.get(self.snapshot.season)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        try:
            week = decode_week(self.snapshot)
        except ProtocolError:
            week = None
        return {
            "kdomo_schedule_revision": week.revision if week else None,
            "kdomo_program_name": week.name if week else None,
            "kdomo_schedule_write_enabled": self.coordinator.schedule_write_enabled,
            "kdomo_mode": self.snapshot.integer("mode"),
            "kdomo_status": self.snapshot.integer("status"),
            "kdomo_program": self.snapshot.integer("program"),
            "kdomo_fancoil": self.snapshot.values.get("fancoil"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if ATTR_TEMPERATURE not in kwargs:
            raise HomeAssistantError("A target temperature is required")
        mode = kwargs.get("hvac_mode")
        if mode is not None and mode not in self.hvac_modes:
            raise HomeAssistantError("Unsupported HVAC mode for the active K-Domo program")
        await self.coordinator.async_command(
            self.device,
            target=kwargs[ATTR_TEMPERATURE],
            operation=mode,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in self.hvac_modes:
            raise HomeAssistantError("Unsupported HVAC mode for the active K-Domo program")
        await self.coordinator.async_command(self.device, operation=hvac_mode)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_command(self.device, operation="on")

    async def async_turn_off(self) -> None:
        await self.coordinator.async_command(self.device, operation="off")
