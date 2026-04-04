"""Sensor platform for FireboardHA."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import FireboardCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FireboardHA sensor entities from a config entry."""
    coordinator: FireboardCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which (uuid, channel) pairs have already been registered.
    known: set[tuple[str, int]] = set()

    def _add_new_entities() -> None:
        """Create sensor entities for any newly discovered channels."""
        if coordinator.data is None:
            return

        devices_by_uuid = {d["uuid"]: d for d in coordinator.data["devices"]}
        new_entities: list[FireboardSensor] = []

        for uuid, channels in coordinator.data["seen_channels"].items():
            device = devices_by_uuid.get(uuid)
            if device is None:
                continue
            for channel in channels:
                key = (uuid, channel)
                if key not in known:
                    known.add(key)
                    new_entities.append(FireboardSensor(coordinator, device, channel))

        if new_entities:
            _LOGGER.debug(
                "Adding %d new FireboardHA sensor(s)", len(new_entities)
            )
            async_add_entities(new_entities)

    # Register entities discovered during the first refresh.
    _add_new_entities()

    # Re-run on every subsequent coordinator update to catch new probes.
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class FireboardSensor(CoordinatorEntity[FireboardCoordinator], SensorEntity):
    """A temperature sensor for one Fireboard probe channel."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FireboardCoordinator,
        device: dict,
        channel: int,
    ) -> None:
        super().__init__(coordinator)
        self._uuid: str = device["uuid"]
        self._channel: int = channel

        self._attr_unique_id = f"{DOMAIN}_{self._uuid}_channel_{channel}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._uuid)},
            name=device["title"],
            manufacturer=MANUFACTURER,
            model=device.get("model", "Fireboard"),
            serial_number=device.get("hardware_id"),
            configuration_url="https://fireboard.io",
        )

    @property
    def name(self) -> str:
        """Return the probe label, falling back to 'Probe N'."""
        if self.coordinator.data is None:
            return f"Probe {self._channel}"
        label = (
            self.coordinator.data["channel_labels"]
            .get(self._uuid, {})
            .get(self._channel, "")
        )
        return label or f"Probe {self._channel}"

    @property
    def available(self) -> bool:
        """Return True only when the coordinator succeeded and the channel has a live reading."""
        if not self.coordinator.last_update_success:
            return False
        if self.coordinator.data is None:
            return False
        return self._channel in self.coordinator.data["temps"].get(self._uuid, {})

    @property
    def native_value(self) -> float | None:
        """Return the current temperature in °F."""
        if self.coordinator.data is None:
            return None
        reading = (
            self.coordinator.data["temps"]
            .get(self._uuid, {})
            .get(self._channel)
        )
        if reading is None:
            return None
        return reading["temp"]
