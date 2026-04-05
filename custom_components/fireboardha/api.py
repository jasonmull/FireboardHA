"""Fireboard API client."""
from __future__ import annotations

import aiohttp

from .const import API_AUTH_URL, API_BASE_URL, API_DEVICES_PATH, API_SESSION_CHART_PATH, API_TEMPS_PATH, API_USER_AGENT


class FireboardApiError(Exception):
    """Generic Fireboard API error."""


class FireboardAuthError(FireboardApiError):
    """Authentication failure."""


async def async_get_token(
    session: aiohttp.ClientSession, username: str, password: str
) -> str:
    """Authenticate with the Fireboard API and return the auth token.

    Raises FireboardAuthError on invalid credentials.
    Raises aiohttp.ClientError on network failures.
    """
    try:
        async with session.post(
            API_AUTH_URL,
            json={"username": username, "password": password},
            headers={"User-Agent": API_USER_AGENT},
        ) as resp:
            if resp.status == 400:
                raise FireboardAuthError("Invalid username or password")
            resp.raise_for_status()
            data = await resp.json()
            return data["key"]
    except (KeyError, ValueError) as err:
        raise FireboardApiError(f"Unexpected auth response: {err}") from err


class FireboardApiClient:
    """Async client for the Fireboard cloud API."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self._token}",
            "User-Agent": API_USER_AGENT,
        }

    async def async_get_devices(self) -> list[dict]:
        """Return all devices on the account, including channel labels."""
        url = f"{API_BASE_URL}{API_DEVICES_PATH}"
        async with self._session.get(url, headers=self._headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_get_temps(self, uuid: str) -> list[dict]:
        """Return latest temperature readings for a device (UUID in path).

        Only returns channels with readings newer than 60 seconds.
        Returns an empty list when no probes are currently active.
        """
        url = f"{API_BASE_URL}{API_TEMPS_PATH.format(uuid=uuid)}"
        async with self._session.get(url, headers=self._headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_get_session_chart(self, session_id: int) -> list[dict]:
        """Return temperature chart data for an active session.

        Returns a list of readings with temp, channel, and degreetype.
        """
        url = f"{API_BASE_URL}{API_SESSION_CHART_PATH.format(session_id=session_id)}"
        async with self._session.get(url, headers=self._headers) as resp:
            resp.raise_for_status()
            return await resp.json()

