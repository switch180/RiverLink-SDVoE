"""Select platform for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_DEVICE_NAME,
    ATTR_SOURCE_DEVICE_NAME,
    ATTR_STREAM_INDEX,
    ATTR_STREAM_TYPE,
    DEFAULT_STREAM_INDEX,
    LOGGER,
)
from .entity import RiverLinkEntity

if TYPE_CHECKING:
    from .coordinator import RiverLinkDataUpdateCoordinator
    from .data import RiverLinkConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RiverLinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = []
    
    # Create one select entity per receiver
    for receiver_id in coordinator.data.get("receivers", {}):
        entities.append(
            RiverLinkReceiverSourceSelect(coordinator, receiver_id)
        )
    
    async_add_entities(entities)


class RiverLinkReceiverSourceSelect(RiverLinkEntity, SelectEntity):
    """Select entity to choose video source for receiver."""
    
    _attr_icon = "mdi:video-input-hdmi"
    
    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        receiver_id: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, receiver_id)
        
        receiver = coordinator.data["receivers"][receiver_id]
        receiver_name = receiver[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{receiver_id}_video_source_select"
        self._attr_name = f"{receiver_name} Video Source"
        self.entity_id = f"select.riverlink_{receiver_name.lower().replace(' ', '_').replace('-', '_')}_video_source"
    
    @property
    def options(self) -> list[str]:
        """Return list of available video sources."""
        transmitters = self.coordinator.data.get("transmitters", {})
        options = ["None"]  # Always include None option
        
        for transmitter in transmitters.values():
            options.append(transmitter[ATTR_DEVICE_NAME])
        
        return options
    
    @property
    def current_option(self) -> str:
        """Return currently selected video source."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return "None"
        
        # Look for HDMI:0 subscription
        for sub in receiver.get("subscriptions", []):
            if (sub.get(ATTR_STREAM_TYPE) == "HDMI" and 
                sub.get(ATTR_STREAM_INDEX) == DEFAULT_STREAM_INDEX):
                source_name = sub.get(ATTR_SOURCE_DEVICE_NAME)
                if source_name:
                    return source_name
        
        return "None"
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes for future multiview support."""
        return {
            ATTR_STREAM_INDEX: DEFAULT_STREAM_INDEX,
            ATTR_STREAM_TYPE: "HDMI",
            "supports_multiview": False,  # Future flag
        }
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected video source."""
        if option == "None":
            # Leave current source
            await self._async_leave_source()
        else:
            # Join new source
            await self._async_join_source(option)
    
    async def _async_leave_source(self) -> None:
        """Leave current video source (HDMI:0 only, audio follows)."""
        try:
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_leave_subscription(
                device_id=self._device_id,
                stream_type="HDMI",
                index=DEFAULT_STREAM_INDEX,
            )
            LOGGER.info(
                "Receiver %s left video source",
                self._device_id,
            )
            # Trigger coordinator refresh
            await self.coordinator.async_request_refresh()
        except Exception as exception:
            LOGGER.error(
                "Failed to leave source for receiver %s: %s",
                self._device_id,
                exception,
            )
            raise
    
    async def _async_join_source(self, transmitter_name: str) -> None:
        """Join new video source (HDMI:0 only, audio follows)."""
        try:
            # Find transmitter ID by name
            transmitters = self.coordinator.data.get("transmitters", {})
            transmitter_id = None
            
            for tx_id, tx_data in transmitters.items():
                if tx_data[ATTR_DEVICE_NAME] == transmitter_name:
                    transmitter_id = tx_id
                    break
            
            if not transmitter_id:
                msg = f"Transmitter '{transmitter_name}' not found"
                LOGGER.error(msg)
                raise ValueError(msg)
            
            # Send join command
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_join_subscription(
                transmitter_id=transmitter_id,
                receiver_id=self._device_id,
                stream_type="HDMI",
                tx_index=DEFAULT_STREAM_INDEX,
                rx_index=DEFAULT_STREAM_INDEX,
            )
            LOGGER.info(
                "Receiver %s joined to transmitter %s",
                self._device_id,
                transmitter_id,
            )
            # Trigger coordinator refresh
            await self.coordinator.async_request_refresh()
        except Exception as exception:
            LOGGER.error(
                "Failed to join receiver %s to %s: %s",
                self._device_id,
                transmitter_name,
                exception,
            )
            raise
