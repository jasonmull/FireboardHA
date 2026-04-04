"""DataUpdateCoordinator for FireboardHA."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FireboardApiClient, FireboardApiError
from .const import DEGREETYPE_CELSIUS, DEGREETYPE_FAHRENHEIT, DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


def _to_fahrenheit(temp: float, degreetype: int) -> float:
    """Convert a temperature value to Fahrenheit if needed."""
    if degreetype == DEGREETYPE_CELSIUS:
        return round((temp * 9 / 5) + 32, 1)
    return temp


class FireboardCoordinator(DataUpdateCoordinator):
    """Coordinator that polls the Fireboard API for all devices and their temps.

    coordinator.data structure:
    {
        "devices": [<raw device dicts from API>],
        "channel_labels": {
            "<uuid>": {<channel_num>: "<label>", ...},
            ...
        },
        "temps": {
            "<uuid>": {
                <channel_num>: {"temp": <float °F>, "degreetype": <int>},
                ...
            },
            ...
        },
        "seen_channels": {
            "<uuid>": {<channel_num>, ...},  # accumulated, never shrinks
            ...
        },
    }
    """

    def __init__(self, hass: HomeAssistant, client: FireboardApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._client = client

    async def _async_update_data(self) -> dict:
        """Fetch latest data from the Fireboard API."""
        try:
            devices = await self._client.async_get_devices()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching Fireboard devices: {err}") from err
        except FireboardApiError as err:
            raise UpdateFailed(str(err)) from err

        _LOGGER.warning("FireboardHA: fetched %d device(s): %s", len(devices), [d.get("uuid") for d in devices])

        channel_labels: dict[str, dict[int, str]] = {}
        temps: dict[str, dict[int, dict]] = {}

        for device in devices:
            uuid = device["uuid"]

            # Channel label index built from device list (labels not in /temps.json)
            # Try both known field names from the API
            channel_labels[uuid] = {
                ch["channel"]: ch.get("label") or ch.get("channel_label", "")
                for ch in device.get("channels", [])
            }

            # Fetch live readings from the dedicated temps endpoint.
            # Isolated per-device: one failing device doesn't block the rest.
            try:
                raw_temps = await self._client.async_get_temps(uuid)
                _LOGGER.warning(
                    "FireboardHA: temps for %s (%s): %s", device.get("title", uuid), uuid, raw_temps
                )
                temps[uuid] = {
                    entry["channel"]: {
                        "temp": _to_fahrenheit(entry["temp"], entry["degreetype"]),
                    }
                    for entry in raw_temps
                }
            except (aiohttp.ClientError, FireboardApiError) as err:
                _LOGGER.warning(
                    "Could not fetch temps for %s (%s): %s",
                    device.get("title", uuid), uuid, err,
                )
                temps[uuid] = {}

        # Accumulate seen channels — never shrinks so entities persist
        # even when probes are temporarily unplugged.
        prev_seen: dict[str, set[int]] = (
            self.data["seen_channels"] if self.data else {}
        )
        seen_channels: dict[str, set[int]] = {}
        for device in devices:
            uuid = device["uuid"]
            device_channels = {ch["channel"] for ch in device.get("channels", [])}
            seen_channels[uuid] = (
                prev_seen.get(uuid, set()) | device_channels | set(temps[uuid].keys())
            )

        return {
            "devices": devices,
            "channel_labels": channel_labels,
            "temps": temps,
            "seen_channels": seen_channels,
        }
