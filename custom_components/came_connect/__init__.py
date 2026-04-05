"""Came Connect integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from .coordinator import CameConnectApiClient, CameConnectCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    client = CameConnectApiClient(
        hass,
        data[CONF_CLIENT_ID],
        data[CONF_CLIENT_SECRET],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )

    coordinator = CameConnectCoordinator(
        hass,
        client,
        data[CONF_DEVICE_ID],
        data.get(CONF_DEVICE_NAME, f"Gate {data[CONF_DEVICE_ID]}"),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as exc:
        raise ConfigEntryNotReady(f"Cannot connect to Came Connect: {exc}") from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
