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
    """Coordinator that polls the Fireboard API for all devices and their temps."""

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

        # Collect the active session ID per device (use the first channel's sessionid).
        # session_id -> uuid mapping so chart readings can be mapped back to a device.
        session_to_uuid: dict[int, str] = {}

        for device in devices:
            uuid = device["uuid"]
            channels = device.get("channels", [])

            channel_labels[uuid] = {
                ch["channel"]: ch.get("channel_label", "")
                for ch in channels
            }

            # Prefer /temps.json — works if readings are < 1 minute old.
            try:
                raw_temps = await self._client.async_get_temps(uuid)
            except (aiohttp.ClientError, FireboardApiError) as err:
                _LOGGER.warning("Could not fetch temps for %s: %s", device.get("title", uuid), err)
                raw_temps = []

            if raw_temps:
                _LOGGER.warning("FireboardHA temps (direct) %s: %s", device.get("title", uuid), raw_temps)
                temps[uuid] = {
                    entry["channel"]: {"temp": _to_fahrenheit(entry["temp"], entry["degreetype"])}
                    for entry in raw_temps
                }
            else:
                temps[uuid] = {}
                # Record session ID so we can fall back to the chart endpoint.
                session_ids = {ch["sessionid"] for ch in channels if ch.get("sessionid")}
                for sid in session_ids:
                    session_to_uuid[sid] = uuid

        # Fall back: fetch session chart data for any device that had no direct readings.
        # The chart endpoint contains the full session history — we take the most recent
        # reading per channel as the current temperature.
        for session_id, uuid in session_to_uuid.items():
            try:
                chart = await self._client.async_get_session_chart(session_id)
                _LOGGER.warning(
                    "FireboardHA chart session %s (last 3 entries): %s",
                    session_id,
                    chart[-3:] if chart else [],
                )
                # chart is a list of readings sorted oldest→newest.
                # Walk in reverse to find the most recent reading per channel.
                latest: dict[int, dict] = {}
                for entry in reversed(chart):
                    ch = entry.get("channel") or entry.get("chan")
                    if ch is not None and ch not in latest:
                        latest[ch] = entry
                    if len(latest) == len(channel_labels.get(uuid, {})):
                        break  # found one reading per channel, stop scanning

                temps[uuid] = {
                    ch: {"temp": _to_fahrenheit(entry["temp"], entry.get("degreetype", 2))}
                    for ch, entry in latest.items()
                    if entry.get("temp") is not None
                }
            except (aiohttp.ClientError, FireboardApiError) as err:
                _LOGGER.warning("Could not fetch chart for session %s: %s", session_id, err)

        # Accumulate seen channels — never shrinks.
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
