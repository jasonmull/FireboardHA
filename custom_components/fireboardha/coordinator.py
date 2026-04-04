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

        # Build channel label index: {uuid: {channel_num: label}}
        channel_labels: dict[str, dict[int, str]] = {}
        for device in devices:
            uuid = device["uuid"]
            channel_labels[uuid] = {
                ch["channel"]: ch.get("label", "")
                for ch in device.get("channels", [])
            }

        # Fetch temps per device; failures are isolated so one bad device
        # does not prevent the rest from updating.
        temps: dict[str, dict[int, dict]] = {}
        for device in devices:
            uuid = device["uuid"]
            try:
                raw = await self._client.async_get_temps(uuid)
                temps[uuid] = {
                    entry["channel"]: {
                        "temp": _to_fahrenheit(entry["temp"], entry["degreetype"]),
                        "degreetype": DEGREETYPE_FAHRENHEIT,  # already converted
                    }
                    for entry in raw
                }
            except (aiohttp.ClientError, FireboardApiError) as err:
                _LOGGER.warning(
                    "Could not fetch temps for device %s (%s): %s",
                    device.get("title", uuid),
                    uuid,
                    err,
                )
                temps[uuid] = {}

        # Accumulate seen channels from:
        #   1. Previous data (never shrink)
        #   2. The device's channel list from /devices.json (always populated,
        #      even when no probe is actively reading)
        #   3. Channels with active readings from /temps.json
        # This ensures entities are created on first load even when probes
        # are not currently sending readings.
        prev_seen: dict[str, set[int]] = (
            self.data["seen_channels"] if self.data else {}
        )
        seen_channels: dict[str, set[int]] = {}
        for device in devices:
            uuid = device["uuid"]
            device_channels = {
                ch["channel"] for ch in device.get("channels", [])
            }
            seen_channels[uuid] = (
                prev_seen.get(uuid, set()) | device_channels | set(temps[uuid].keys())
            )

        return {
            "devices": devices,
            "channel_labels": channel_labels,
            "temps": temps,
            "seen_channels": seen_channels,
        }
