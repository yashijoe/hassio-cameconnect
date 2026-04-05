"""Config flow for Came Connect."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class CameConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Came Connect config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, Any] = {}
        self._discovered_devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            from .coordinator import CameConnectApiClient

            client = CameConnectApiClient(
                self.hass,
                user_input[CONF_CLIENT_ID],
                user_input[CONF_CLIENT_SECRET],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.async_validate_credentials()
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during credential validation")
                errors["base"] = "cannot_connect"
            else:
                self._credentials = user_input
                # Try device discovery
                devices = await client.async_list_devices()
                if devices:
                    self._discovered_devices = devices
                    return await self.async_step_device()
                # No discovery — ask for manual device ID
                return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_CREDENTIALS_SCHEMA,
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            # Resolve name from discovered list if available
            device_name = user_input.get(CONF_DEVICE_NAME)
            if not device_name:
                match = next(
                    (d for d in self._discovered_devices if d["id"] == device_id), None
                )
                device_name = match["name"] if match else f"Gate {device_id}"

            await self.async_set_unique_id(f"{DOMAIN}_{device_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=device_name,
                data={
                    **self._credentials,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: device_name,
                },
            )

        if self._discovered_devices:
            device_options = {d["id"]: f"{d['name']} (ID: {d['id']})" for d in self._discovered_devices}
            schema = vol.Schema(
                {vol.Required(CONF_DEVICE_ID): vol.In(device_options)}
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): vol.Coerce(int),
                    vol.Optional(CONF_DEVICE_NAME, default=""): str,
                }
            )

        return self.async_show_form(
            step_id="device",
            data_schema=schema,
            errors=errors,
        )
