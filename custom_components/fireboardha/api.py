"""Fireboard API client."""
from __future__ import annotations

import aiohttp

from .const import API_AUTH_URL, API_BASE_URL, API_DEVICES_PATH, API_USER_AGENT


class FireboardApiError(Exception):
    """Generic Fireboard API error."""


class FireboardAuthError(FireboardApiError):
    """Authentication failure."""


async def async_get_token(
    session: aiohttp.ClientSession, username: str, password: str
) -> str:
    """Authenticate with the Fireboard API and return the auth token."""
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
        """Return all devices with channel metadata and latest_temps."""
        url = f"{API_BASE_URL}{API_DEVICES_PATH}"
        async with self._session.get(url, headers=self._headers) as resp:
            resp.raise_for_status()
            return await resp.json()
