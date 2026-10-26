"""Shared device identity and availability."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KdomoCoordinator
from .models import Device, Snapshot


class KdomoEntity(CoordinatorEntity[KdomoCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KdomoCoordinator, device: Device, suffix: str) -> None:
        super().__init__(coordinator, context=device.key)
        self.device = device
        self._attr_unique_id = f"{device.key}:{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.key)},
            name=device.name,
            manufacturer="Giacomini",
            model="K-Domo cloud thermostat",
        )

    @property
    def snapshot(self) -> Snapshot:
        return (self.coordinator.data or {}).get(self.device.key, Snapshot())

    @property
    def available(self) -> bool:
        return super().available and self.snapshot.online and not self.snapshot.error
