"""Config flow for FireboardHA."""
from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FireboardAuthError, async_get_token
from .const import CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class FireboardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the FireboardHA config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Show the credentials form and validate on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username: str = user_input[CONF_USERNAME]
            password: str = user_input[CONF_PASSWORD]

            try:
                session = async_get_clientsession(self.hass)
                token = await async_get_token(session, username, password)
            except FireboardAuthError:
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Fireboard authentication")
                errors["base"] = "unknown"
            else:
                # Prevent configuring the same account twice.
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_TOKEN: token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
