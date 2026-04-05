"""DataUpdateCoordinator for FireboardHA."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FireboardApiClient, FireboardApiError
from .const import DEGREETYPE_CELSIUS, DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


def _to_fahrenheit(temp: float, degreetype: int) -> float:
    """Convert a temperature value to Fahrenheit if needed."""
    if degreetype == DEGREETYPE_CELSIUS:
        return round((temp * 9 / 5) + 32, 1)
    return temp


class FireboardCoordinator(DataUpdateCoordinator):
    """Coordinator that polls the Fireboard API for all devices and their temps.

    Uses a single GET /devices.json call per poll. The response includes
    channel metadata and a latest_temps array (readings < 60s old) for each
    device, so no per-device temp calls are needed.
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

        channel_labels: dict[str, dict[int, str]] = {}
        temps: dict[str, dict[int, dict]] = {}

        for device in devices:
            uuid = device["uuid"]
            channels = device.get("channels", [])
            device_degreetype = device.get("degreetype", 2)

            channel_labels[uuid] = {
                ch["channel"]: ch.get("channel_label", "")
                for ch in channels
            }

            # latest_temps is populated by the API for readings < 60s old.
            # Each entry: {"temp": <float>, "channel": <int>, "degreetype": <int>, ...}
            temps[uuid] = {
                entry["channel"]: {
                    "temp": _to_fahrenheit(
                        entry["temp"],
                        entry.get("degreetype", device_degreetype),
                    ),
                }
                for entry in device.get("latest_temps", [])
                if entry.get("temp") is not None
            }

        # Accumulate seen channels — never shrinks so entities persist
        # for probes that are temporarily unplugged.
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
