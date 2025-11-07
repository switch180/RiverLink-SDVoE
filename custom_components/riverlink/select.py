"""Select platform for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_DEVICE_NAME,
    ATTR_DISPLAY_MODE,
    ATTR_RESOLUTION_APPLIES,
    ATTR_RESOLUTION_FPS,
    ATTR_RESOLUTION_HEIGHT,
    ATTR_RESOLUTION_PRESET,
    ATTR_RESOLUTION_WIDTH,
    ATTR_SOURCE_DEVICE_NAME,
    ATTR_STREAM_INDEX,
    ATTR_STREAM_TYPE,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_RESOLUTION_PRESET,
    DEFAULT_STREAM_INDEX,
    DISPLAY_MODE_FASTSWITCH,
    DISPLAY_MODE_FASTSWITCH_CROP,
    DISPLAY_MODE_FASTSWITCH_STRETCH,
    DISPLAY_MODE_GENLOCK,
    DISPLAY_MODE_GENLOCK_SCALING,
    LOGGER,
    RESOLUTION_PRESETS,
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
    
    # Create select entities per receiver
    for receiver_id in coordinator.data.get("receivers", {}):
        entities.append(
            RiverLinkReceiverSourceSelect(coordinator, receiver_id)
        )
        entities.append(
            RiverLinkDisplayModeSelect(coordinator, receiver_id)
        )
        entities.append(
            RiverLinkResolutionPresetSelect(coordinator, receiver_id)
        )
    
    async_add_entities(entities)


class RiverLinkReceiverSourceSelect(RiverLinkEntity, SelectEntity):
    """Select entity to choose video source for receiver."""
    
    _attr_icon = "mdi:video-input-hdmi"
    _attr_translation_key = "video_source"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        receiver_id: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, receiver_id)
        self._attr_unique_id = f"{receiver_id}_video_source_select"
    
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


class RiverLinkDisplayModeSelect(RiverLinkEntity, SelectEntity):
    """Select entity for choosing video display mode."""
    
    _attr_icon = "mdi:monitor-arrow-down-variant"
    _attr_translation_key = "display_mode"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        receiver_id: str,
    ) -> None:
        """Initialize display mode select."""
        super().__init__(coordinator, receiver_id)
        self._attr_unique_id = f"{receiver_id}_display_mode"
    
    @property
    def options(self) -> list[str]:
        """Return display mode options (keys for translation)."""
        return [
            DISPLAY_MODE_GENLOCK,
            DISPLAY_MODE_GENLOCK_SCALING,
            DISPLAY_MODE_FASTSWITCH,
            DISPLAY_MODE_FASTSWITCH_STRETCH,
            DISPLAY_MODE_FASTSWITCH_CROP,
        ]
    
    @property
    def current_option(self) -> str:
        """Return currently selected display mode (key)."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return DEFAULT_DISPLAY_MODE
        
        return receiver.get(ATTR_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        mode = receiver.get(ATTR_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)
        
        return {
            "mode_type": mode,
            "requires_resolution": mode != DISPLAY_MODE_GENLOCK,
            "latency_type": "zero-frame" if mode.startswith("genlock") else "fast-switch",
        }
    
    async def async_select_option(self, option: str) -> None:
        """Change display mode."""
        # Validate mode
        if option not in [DISPLAY_MODE_GENLOCK, DISPLAY_MODE_GENLOCK_SCALING,
                         DISPLAY_MODE_FASTSWITCH, DISPLAY_MODE_FASTSWITCH_STRETCH,
                         DISPLAY_MODE_FASTSWITCH_CROP]:
            raise ValueError(f"Unknown display mode: {option}")
        
        # Get current resolution from receiver data
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        width = receiver.get(ATTR_RESOLUTION_WIDTH, 1920)
        height = receiver.get(ATTR_RESOLUTION_HEIGHT, 1080)
        fps = receiver.get(ATTR_RESOLUTION_FPS, 60)
        
        # Send command
        client = self.coordinator.config_entry.runtime_data.client
        
        try:
            if option == DISPLAY_MODE_GENLOCK:
                # Genlock doesn't need resolution
                await client.async_set_video_mode(
                    device_id=self._device_id,
                    mode=option,
                )
            else:
                # All other modes need resolution
                await client.async_set_video_mode(
                    device_id=self._device_id,
                    mode=option,
                    width=width,
                    height=height,
                    fps=fps,
                )
            
            # Update coordinator data
            receiver[ATTR_DISPLAY_MODE] = option
            receiver[ATTR_RESOLUTION_APPLIES] = option != DISPLAY_MODE_GENLOCK
            
            LOGGER.info(
                "Receiver %s display mode changed to %s",
                self._device_id,
                option,
            )
            
            await self.coordinator.async_request_refresh()
        except Exception as exception:
            LOGGER.error(
                "Failed to set display mode for receiver %s: %s",
                self._device_id,
                exception,
            )
            raise


class RiverLinkResolutionPresetSelect(RiverLinkEntity, SelectEntity):
    """Select entity for choosing resolution preset."""
    
    _attr_icon = "mdi:monitor-shimmer"
    _attr_translation_key = "resolution_preset"
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        receiver_id: str,
    ) -> None:
        """Initialize resolution preset select."""
        super().__init__(coordinator, receiver_id)
        self._attr_unique_id = f"{receiver_id}_resolution_preset"
    
    @property
    def options(self) -> list[str]:
        """Return resolution preset options."""
        return list(RESOLUTION_PRESETS.keys())
    
    @property
    def current_option(self) -> str | None:
        """Return currently selected resolution preset, or None if custom."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return DEFAULT_RESOLUTION_PRESET
        
        preset = receiver.get(ATTR_RESOLUTION_PRESET, DEFAULT_RESOLUTION_PRESET)
        
        # If custom resolution, return None (check extra_state_attributes for actual values)
        if preset == "Custom":
            return None
        
        # Otherwise show preset with status suffix
        applies = receiver.get(ATTR_RESOLUTION_APPLIES, True)
        if applies:
            return f"{preset} ✓"
        else:
            return f"{preset} (Stored)"
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        
        return {
            ATTR_RESOLUTION_WIDTH: receiver.get(ATTR_RESOLUTION_WIDTH, 1920),
            ATTR_RESOLUTION_HEIGHT: receiver.get(ATTR_RESOLUTION_HEIGHT, 1080),
            ATTR_RESOLUTION_FPS: receiver.get(ATTR_RESOLUTION_FPS, 60),
            ATTR_RESOLUTION_APPLIES: receiver.get(ATTR_RESOLUTION_APPLIES, True),
            "category": "broadcast" if receiver.get(ATTR_RESOLUTION_HEIGHT, 1080) <= 2160 else "monitor",
        }
    
    async def async_select_option(self, option: str) -> None:
        """Change resolution preset."""
        # Strip suffix if present
        clean_option = option.replace(" ✓", "").replace(" (Stored)", "")
        
        # Get resolution values
        if clean_option not in RESOLUTION_PRESETS:
            raise ValueError(f"Unknown resolution preset: {clean_option}")
        
        width, height, fps = RESOLUTION_PRESETS[clean_option]
        
        # Get current display mode
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        mode = receiver.get(ATTR_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)
        
        # Update stored resolution
        receiver[ATTR_RESOLUTION_WIDTH] = width
        receiver[ATTR_RESOLUTION_HEIGHT] = height
        receiver[ATTR_RESOLUTION_FPS] = fps
        receiver[ATTR_RESOLUTION_PRESET] = clean_option
        
        try:
            # Apply resolution for all modes except genlock
            if mode in [DISPLAY_MODE_GENLOCK_SCALING, DISPLAY_MODE_FASTSWITCH,
                       DISPLAY_MODE_FASTSWITCH_STRETCH, DISPLAY_MODE_FASTSWITCH_CROP]:
                client = self.coordinator.config_entry.runtime_data.client
                await client.async_set_video_mode(
                    device_id=self._device_id,
                    mode=mode,
                    width=width,
                    height=height,
                    fps=fps,
                )
                receiver[ATTR_RESOLUTION_APPLIES] = True
                LOGGER.info(
                    "Receiver %s resolution changed to %s (%dx%d @ %d fps)",
                    self._device_id,
                    clean_option,
                    width,
                    height,
                    fps,
                )
            elif mode == DISPLAY_MODE_GENLOCK:
                # In genlock mode, just store it
                receiver[ATTR_RESOLUTION_APPLIES] = False
                LOGGER.info(
                    "Receiver %s resolution stored: %s (will apply when switching from genlock)",
                    self._device_id,
                    clean_option,
                )
            
            await self.coordinator.async_request_refresh()
        except Exception as exception:
            LOGGER.error(
                "Failed to set resolution for receiver %s: %s",
                self._device_id,
                exception,
            )
            raise
