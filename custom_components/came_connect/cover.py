"""Cover platform for Came Connect gates."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CMD_CLOSE, CMD_OPEN, CMD_STOP, CONF_DEVICE_NAME, DOMAIN
from .coordinator import CameConnectCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CameConnectCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CameConnectCover(coordinator, entry)])


class CameConnectCover(CoordinatorEntity[CameConnectCoordinator], CoverEntity):
    """Representation of a Came Connect gate as a Cover entity."""

    _attr_device_class = CoverDeviceClass.GATE
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    _attr_has_entity_name = True
    _attr_name = None  # Use device name as entity name

    def __init__(
        self,
        coordinator: CameConnectCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.device_id))},
            name=entry.data.get(CONF_DEVICE_NAME, f"Gate {coordinator.device_id}"),
            manufacturer="CAME",
            model="Came Connect",
        )

    @property
    def is_closed(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("state") == "closed"

    @property
    def is_opening(self) -> bool:
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get("state") == "opening"

    @property
    def is_closing(self) -> bool:
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get("state") == "closing"

    @property
    def current_cover_position(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("position")

    @property
    def available(self) -> bool:
        return super().available and bool(
            self.coordinator.data and self.coordinator.data.get("online", True)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "direction": data.get("direction"),
            "raw_code": data.get("raw_code"),
            "maneuvers": data.get("maneuvers"),
            "updated_at": data.get("updated_at"),
            "device_id": self.coordinator.device_id,
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_send_command(
            self.coordinator.device_id, CMD_OPEN
        )
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_send_command(
            self.coordinator.device_id, CMD_CLOSE
        )
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_send_command(
            self.coordinator.device_id, CMD_STOP
        )
        await self.coordinator.async_request_refresh()
