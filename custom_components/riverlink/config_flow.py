"""Adds config flow for RiverLink SDVoE Matrix."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .api import (
    RiverLinkApiClient,
    RiverLinkApiClientCommunicationError,
    RiverLinkApiClientConnectionError,
    RiverLinkApiClientError,
)
from .const import (
    CONF_API_VERSION,
    DEFAULT_API_VERSION,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
    LOGGER,
)


class RiverLinkFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for RiverLink SDVoE Matrix."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_connection(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                    api_version=user_input[CONF_API_VERSION],
                )
            except RiverLinkApiClientConnectionError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "cannot_connect"
            except RiverLinkApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "cannot_connect"
            except RiverLinkApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Use host:port as unique_id
                unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"SDVoE Matrix ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                    ): cv.string,
                    vol.Required(
                        CONF_PORT,
                        default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT),
                    ): cv.port,
                    vol.Required(
                        CONF_API_VERSION,
                        default=(user_input or {}).get(CONF_API_VERSION, DEFAULT_API_VERSION),
                    ): cv.string,
                },
            ),
            errors=_errors,
        )

    async def _test_connection(
        self, host: str, port: int, api_version: str
    ) -> None:
        """Test connection to the SDVoE API server."""
        client = RiverLinkApiClient(
            host=host,
            port=port,
            api_version=api_version,
        )
        try:
            # Test connection and API version
            if not await client.connect():
                raise RiverLinkApiClientConnectionError(
                    "Failed to connect or load API version"
                )
            
            # Test getting device data
            await client.async_get_data()
            
        finally:
            await client.disconnect()
