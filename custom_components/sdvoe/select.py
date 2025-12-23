"""Select platform for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .api import RiverLinkApiClientError
from .const import (
    ATTR_DEVICE_NAME,
    ATTR_DISPLAY_MODE,
    ATTR_PENDING_RESOLUTION_PRESET,
    ATTR_RESOLUTION_APPLIES,
    ATTR_RESOLUTION_FPS,
    ATTR_RESOLUTION_HEIGHT,
    ATTR_RESOLUTION_PRESET,
    ATTR_RESOLUTION_PRESET_STATUS,
    ATTR_RESOLUTION_WIDTH,
    ATTR_SOURCE_DEVICE_ID,
    ATTR_STREAM_INDEX,
    ATTR_STREAM_STATE,
    ATTR_STREAM_TYPE,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_RESOLUTION_PRESET,
    DEFAULT_STREAM_INDEX,
    DISPLAY_MODE_FASTSWITCH,
    DISPLAY_MODE_FASTSWITCH_CROP,
    DISPLAY_MODE_FASTSWITCH_STRETCH,
    DISPLAY_MODE_GENLOCK,
    DISPLAY_MODE_GENLOCK_SCALING,
    DOMAIN,
    LOGGER,
    PRESET_STATUS_APPLIED,
    PRESET_STATUS_PENDING,
    PRESET_STATUS_STORED,
    RESOLUTION_4K_HEIGHT,
    RESOLUTION_PRESETS,
    STATE_STOPPED,
    STREAM_TYPE_HDMI,
)
from .entity import RiverLinkEntity
from .errors import (
    ERROR_UI_JOIN_FAILED,
    ERROR_UI_LEAVE_FAILED,
    ERROR_UNKNOWN_MODE,
    ERROR_UNKNOWN_PRESET,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import RiverLinkDataUpdateCoordinator
    from .data import RiverLinkConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RiverLinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = []

    # Create select entities per receiver
    for receiver_id in coordinator.data.get("receivers", {}):
        entities.append(RiverLinkReceiverSourceSelect(coordinator, receiver_id))
        entities.append(RiverLinkDisplayModeSelect(coordinator, receiver_id))
        entities.append(RiverLinkResolutionPresetSelect(coordinator, receiver_id))

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

    def _get_device_friendly_name(self, device_id: str, fallback_name: str) -> str:
        """
        Return friendly name for a device_id using the device registry.

        Preference order:
        1. User-defined name (name_by_user)
        2. Registry name
        3. Fallback API/device name
        """
        device_reg = dr.async_get(self.hass)
        device = device_reg.async_get_device(identifiers={(DOMAIN, device_id)})

        if device and device.name_by_user:
            return device.name_by_user
        if device and device.name:
            return device.name
        return fallback_name

    def _make_option_label(self, tx_id: str, tx_data: dict[str, Any]) -> str:
        """Make a human-readable option label 'Friendly (DEVICE_ID)'."""
        base_name = tx_data.get(ATTR_DEVICE_NAME, tx_id)
        friendly_name = self._get_device_friendly_name(tx_id, base_name)
        return f"{friendly_name} ({tx_id})"

    def _get_device_id_from_option(self, option: str) -> str | None:
        """
        Extract the device_id from a select option label.

        Expects format 'Friendly Name (DEVICE_ID)'.
        """
        # Find the last ' (' and closing ')'
        # This is more robust against parentheses in the friendly name itself.
        start = option.rfind(" (")
        end = option.rfind(")")
        if start == -1 or end == -1 or end < start:
            return None
        # device_id is what's inside the parentheses
        return option[start + 2 : end].strip()

    @property
    def options(self) -> list[str]:
        """Return list of available video sources as 'Friendly (DEVICE_ID)'."""
        transmitters = self.coordinator.data.get("transmitters", {})
        # Sort for deterministic order (by tx_id)
        labels = [self._make_option_label(tx_id, tx_data) for tx_id, tx_data in sorted(transmitters.items())]
        # Include "None" at the top to allow disconnect
        return ["None", *labels]

    @property
    def current_option(self) -> str:
        """Return currently selected video source with friendly name."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return "None"

        # Look for HDMI:0 subscription
        source_device_id: str | None = None
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == "HDMI" and sub.get(ATTR_STREAM_INDEX) == DEFAULT_STREAM_INDEX:
                source_device_id = sub.get(ATTR_SOURCE_DEVICE_ID)
                break

        if not source_device_id:
            return "None"

        transmitters = self.coordinator.data.get("transmitters", {})
        tx_data = transmitters.get(source_device_id)
        if not tx_data:
            return "None"

        return self._make_option_label(source_device_id, tx_data)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes including current transmitter_id."""
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        source_device_id: str | None = None

        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == "HDMI" and sub.get(ATTR_STREAM_INDEX) == DEFAULT_STREAM_INDEX:
                source_device_id = sub.get(ATTR_SOURCE_DEVICE_ID)
                break

        return {
            ATTR_STREAM_INDEX: DEFAULT_STREAM_INDEX,
            ATTR_STREAM_TYPE: "HDMI",
            "current_transmitter_id": source_device_id,
            "supports_multiview": False,  # Future flag
        }

    def _find_hdmi_stream(self, tx_data: dict[str, Any], index: int = DEFAULT_STREAM_INDEX) -> dict[str, Any] | None:
        """
        Find HDMI stream by index in transmitter data.

        Args:
            tx_data: Transmitter device data from coordinator
            index: Stream index to find (default: DEFAULT_STREAM_INDEX)

        Returns:
            Stream dict if found, None otherwise

        """
        if not tx_data:
            return None

        for stream in tx_data.get("streams", []):
            if (
                stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI
                and stream.get(ATTR_STREAM_INDEX) == index
            ):
                return stream

        return None

    async def async_select_option(self, option: str) -> None:
        """
        Handle user selection with auto-start support.

        'None' → disconnect / unroute the receiver.
        Otherwise → join the selected transmitter (auto-starting stream if needed).
        """
        # Handle disconnect case
        if option == "None":
            await self._async_leave_source()
            return

        # Parse device_id from the label
        transmitter_id = self._get_device_id_from_option(option)
        if not transmitter_id:
            LOGGER.error(
                "Invalid option '%s' for %s; cannot parse transmitter id",
                option,
                self.entity_id,
            )
            msg = f"Invalid option: {option}"
            raise ValueError(msg)

        # Check if transmitter stream is stopped and auto-start if needed
        transmitters = self.coordinator.data.get("transmitters", {})
        tx_data = transmitters.get(transmitter_id)
        hdmi_stream = self._find_hdmi_stream(tx_data, DEFAULT_STREAM_INDEX)

        if hdmi_stream and hdmi_stream.get(ATTR_STREAM_STATE) == STATE_STOPPED:
            # Auto-start the stream
            tx_name = tx_data.get(ATTR_DEVICE_NAME, transmitter_id) if tx_data else transmitter_id
            LOGGER.info(
                "Auto-starting stopped HDMI:%d stream for transmitter %s (%s) before join",
                DEFAULT_STREAM_INDEX,
                transmitter_id,
                tx_name,
            )

            try:
                client = self.coordinator.config_entry.runtime_data.client
                await client.async_start_stream(
                    device_id=transmitter_id,
                    stream_type=STREAM_TYPE_HDMI,
                    stream_index=DEFAULT_STREAM_INDEX,
                )
                # NO SLEEP - rely on join retry logic to handle timing
            except RiverLinkApiClientError as exc:
                LOGGER.warning(
                    "Failed to auto-start stream for %s: %s. Attempting join anyway.",
                    transmitter_id,
                    exc,
                )
                # Continue anyway - join retry may still work

        await self._async_join_source(transmitter_id)

    async def _async_leave_source(self) -> None:
        """Leave current video and audio sources."""
        try:
            client = self.coordinator.config_entry.runtime_data.client

            # Leave HDMI video stream
            await client.async_leave_subscription(
                device_id=self._device_id,
                stream_type="HDMI",
                index=DEFAULT_STREAM_INDEX,
            )

            # Leave HDMI audio stream
            await client.async_leave_subscription(
                device_id=self._device_id,
                stream_type="HDMI_AUDIO",
                index=DEFAULT_STREAM_INDEX,
            )

            LOGGER.info(
                "Receiver %s left video and audio sources",
                self._device_id,
            )

            # NOTE: Intentionally NOT refreshing coordinator here to prevent race condition.
            # See issue #22: https://github.com/switch180/RiverLink-SDVoE/issues/22
            #
            # If user immediately selects another source after "None", the join operation
            # will trigger a refresh after hardware processes both commands. This prevents
            # the leave's refresh from showing "None" before join completes.
            #
            # If "None" was the final selection, regular polling (5s) will pick up the change.
        except RiverLinkApiClientError as exc:
            LOGGER.error(
                "Failed to leave source for receiver %s: %s",
                self._device_id,
                exc,
            )
            msg = ERROR_UI_LEAVE_FAILED.format(error=str(exc))
            raise HomeAssistantError(msg) from exc
        except Exception as exception:
            LOGGER.error(
                "Failed to leave source for receiver %s: %s",
                self._device_id,
                exception,
            )
            raise

    async def _async_join_source(self, transmitter_id: str) -> None:
        """Join video and audio sources using transmitter device_id."""
        try:
            client = self.coordinator.config_entry.runtime_data.client

            # Join HDMI video stream
            await client.async_join_subscription(
                transmitter_id=transmitter_id,
                receiver_id=self._device_id,
                stream_type="HDMI",
                tx_index=DEFAULT_STREAM_INDEX,
                rx_index=DEFAULT_STREAM_INDEX,
            )

            # Join HDMI audio stream
            await client.async_join_subscription(
                transmitter_id=transmitter_id,
                receiver_id=self._device_id,
                stream_type="HDMI_AUDIO",
                tx_index=DEFAULT_STREAM_INDEX,
                rx_index=DEFAULT_STREAM_INDEX,
            )

            LOGGER.info(
                "Receiver %s joined video and audio to transmitter %s",
                self._device_id,
                transmitter_id,
            )
            # Trigger coordinator refresh after both operations complete
            await self.coordinator.async_request_refresh()
        except RiverLinkApiClientError as exc:
            LOGGER.error(
                "Failed to join receiver %s to %s: %s",
                self._device_id,
                transmitter_id,
                exc,
            )
            msg = ERROR_UI_JOIN_FAILED.format(error=str(exc))
            raise HomeAssistantError(msg) from exc
        except Exception as exception:
            LOGGER.error(
                "Failed to join receiver %s to %s: %s",
                self._device_id,
                transmitter_id,
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
        if option not in [
            DISPLAY_MODE_GENLOCK,
            DISPLAY_MODE_GENLOCK_SCALING,
            DISPLAY_MODE_FASTSWITCH,
            DISPLAY_MODE_FASTSWITCH_STRETCH,
            DISPLAY_MODE_FASTSWITCH_CROP,
        ]:
            raise ValueError(ERROR_UNKNOWN_MODE.format(mode=option))

        # Get receiver data
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})

        # Check if there's a pending preset to use
        pending_preset = receiver.get(ATTR_PENDING_RESOLUTION_PRESET)
        if pending_preset and option != DISPLAY_MODE_GENLOCK:
            # Use pending preset resolution
            width, height, fps = RESOLUTION_PRESETS[pending_preset]
            # Clear pending preset after using it
            receiver[ATTR_PENDING_RESOLUTION_PRESET] = None
        else:
            # Use current resolution from device
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
        """Return currently selected or pending resolution preset."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return DEFAULT_RESOLUTION_PRESET

        mode = receiver.get(ATTR_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)

        # If in genlock mode and there's a pending preset, show it
        if mode == DISPLAY_MODE_GENLOCK:
            pending = receiver.get(ATTR_PENDING_RESOLUTION_PRESET)
            if pending:
                return pending

        # Otherwise show actual preset
        preset = receiver.get(ATTR_RESOLUTION_PRESET, DEFAULT_RESOLUTION_PRESET)
        if preset == "Custom":
            return None

        return preset

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})

        mode = receiver.get(ATTR_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)
        applies = receiver.get(ATTR_RESOLUTION_APPLIES, True)
        pending = receiver.get(ATTR_PENDING_RESOLUTION_PRESET)

        if mode == DISPLAY_MODE_GENLOCK and pending:
            status_key = PRESET_STATUS_PENDING  # Pending preset in genlock mode
        elif applies:
            status_key = PRESET_STATUS_APPLIED  # Stored and applied
        else:
            status_key = PRESET_STATUS_STORED  # Stored but not applied

        attrs = {
            ATTR_RESOLUTION_WIDTH: receiver.get(ATTR_RESOLUTION_WIDTH, 1920),
            ATTR_RESOLUTION_HEIGHT: receiver.get(ATTR_RESOLUTION_HEIGHT, 1080),
            ATTR_RESOLUTION_FPS: receiver.get(ATTR_RESOLUTION_FPS, 60),
            ATTR_RESOLUTION_APPLIES: applies,
            "category": "broadcast"
            if receiver.get(ATTR_RESOLUTION_HEIGHT, 1080) <= RESOLUTION_4K_HEIGHT
            else "monitor",
            ATTR_RESOLUTION_PRESET_STATUS: status_key,
        }

        # Include pending preset if set
        if pending:
            attrs[ATTR_PENDING_RESOLUTION_PRESET] = pending

        return attrs

    async def async_select_option(self, option: str) -> None:
        """Change resolution preset."""
        # Get resolution values
        if option not in RESOLUTION_PRESETS:
            raise ValueError(ERROR_UNKNOWN_PRESET.format(preset=option))

        width, height, fps = RESOLUTION_PRESETS[option]

        # Get current display mode
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        mode = receiver.get(ATTR_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)

        try:
            # Apply resolution immediately for all modes except genlock
            if mode in [
                DISPLAY_MODE_GENLOCK_SCALING,
                DISPLAY_MODE_FASTSWITCH,
                DISPLAY_MODE_FASTSWITCH_STRETCH,
                DISPLAY_MODE_FASTSWITCH_CROP,
            ]:
                client = self.coordinator.config_entry.runtime_data.client
                await client.async_set_video_mode(
                    device_id=self._device_id,
                    mode=mode,
                    width=width,
                    height=height,
                    fps=fps,
                )
                LOGGER.info(
                    "Receiver %s resolution applied: %s (%dx%d @ %d fps)",
                    self._device_id,
                    option,
                    width,
                    height,
                    fps,
                )
                # Refresh to get actual device state
                await self.coordinator.async_request_refresh()

            elif mode == DISPLAY_MODE_GENLOCK:
                # In genlock mode, store as pending (persists across refreshes)
                receiver[ATTR_PENDING_RESOLUTION_PRESET] = option
                LOGGER.info(
                    "Receiver %s pending resolution set: %s (will apply when switching from genlock)",
                    self._device_id,
                    option,
                )
                # Don't refresh - keep the pending value in coordinator data

        except Exception as exception:
            LOGGER.error(
                "Failed to set resolution for receiver %s: %s",
                self._device_id,
                exception,
            )
            raise
