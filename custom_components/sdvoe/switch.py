"""Switch platform for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .api import RiverLinkApiClientError
from .const import (
    ATTR_STREAM_ADDRESS,
    ATTR_STREAM_ENABLED,
    ATTR_STREAM_INDEX,
    ATTR_STREAM_STATE,
    ATTR_STREAM_TYPE,
    LOGGER,
    STATE_STREAMING,
    STREAM_TYPE_HDMI,
)
from .errors import (
    ERROR_START_STREAM_FAILED,
    ERROR_STOP_STREAM_FAILED,
)
from .entity import RiverLinkEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import RiverLinkDataUpdateCoordinator
    from .data import RiverLinkConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: RiverLinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up transmitter stream switch entities."""
    coordinator = entry.runtime_data.coordinator

    # Create switch entities for all transmitter HDMI streams
    switches = []

    transmitters = coordinator.data.get("transmitters", {})
    for device_id, tx_data in transmitters.items():
        device_name = tx_data.get("device_name", device_id)

        # Create switch for each HDMI stream
        for stream in tx_data.get("streams", []):
            if stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI:
                stream_index = stream.get(ATTR_STREAM_INDEX, 0)
                switches.append(
                    TransmitterStreamSwitch(
                        coordinator=coordinator,
                        device_id=device_id,
                        device_name=device_name,
                        stream_index=stream_index,
                    )
                )

    LOGGER.debug("Creating %d transmitter stream switch entities", len(switches))
    async_add_entities(switches)


class TransmitterStreamSwitch(RiverLinkEntity, SwitchEntity):
    """Switch entity to control transmitter stream start/stop."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
        device_name: str,
        stream_index: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)

        self._device_name = device_name
        self._stream_index = stream_index

        # Entity configuration
        self._attr_unique_id = f"{device_id}_hdmi_stream_{stream_index}"
        self._attr_name = f"HDMI Stream {stream_index}"
        self._attr_translation_key = "transmitter_stream"

    def _get_stream_data(self) -> dict[str, Any] | None:
        """Get stream data from coordinator."""
        transmitters = self.coordinator.data.get("transmitters", {})
        tx_data = transmitters.get(self._device_id)

        if not tx_data:
            return None

        # Find matching HDMI stream by index
        for stream in tx_data.get("streams", []):
            if (
                stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI
                and stream.get(ATTR_STREAM_INDEX) == self._stream_index
            ):
                return stream

        return None

    @property
    def is_on(self) -> bool:
        """Return true if stream is STREAMING."""
        stream = self._get_stream_data()
        if not stream:
            return False

        state = stream.get(ATTR_STREAM_STATE, "STOPPED")
        return state == STATE_STREAMING

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        return "mdi:cast" if self.is_on else "mdi:cast-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return stream details as attributes."""
        stream = self._get_stream_data()
        if not stream:
            return {}

        return {
            ATTR_STREAM_TYPE: STREAM_TYPE_HDMI,
            ATTR_STREAM_INDEX: self._stream_index,
            ATTR_STREAM_ADDRESS: stream.get(ATTR_STREAM_ADDRESS),
            ATTR_STREAM_ENABLED: stream.get(ATTR_STREAM_ENABLED),
            ATTR_STREAM_STATE: stream.get(ATTR_STREAM_STATE),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002 Unused method argument
        """Start the transmitter stream."""
        try:
            LOGGER.debug(
                "Turning on stream switch: %s HDMI:%d",
                self._device_id,
                self._stream_index,
            )

            await self.coordinator.config_entry.runtime_data.client.async_start_stream(
                device_id=self._device_id,
                stream_type=STREAM_TYPE_HDMI,
                stream_index=self._stream_index,
            )

            # Request immediate refresh to update state
            await self.coordinator.async_request_refresh()

        except RiverLinkApiClientError as err:
            msg = ERROR_START_STREAM_FAILED.format(
                stream_type=STREAM_TYPE_HDMI,
                index=self._stream_index,
                device_id=self._device_id,
                message=str(err),
            )
            LOGGER.error(msg)
            raise HomeAssistantError(msg) from err

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002 Unused method argument
        """Stop the transmitter stream."""
        try:
            LOGGER.debug(
                "Turning off stream switch: %s HDMI:%d",
                self._device_id,
                self._stream_index,
            )

            await self.coordinator.config_entry.runtime_data.client.async_stop_stream(
                device_id=self._device_id,
                stream_type=STREAM_TYPE_HDMI,
                stream_index=self._stream_index,
            )

            # Request immediate refresh to update state
            await self.coordinator.async_request_refresh()

        except RiverLinkApiClientError as err:
            msg = ERROR_STOP_STREAM_FAILED.format(
                stream_type=STREAM_TYPE_HDMI,
                index=self._stream_index,
                device_id=self._device_id,
                message=str(err),
            )
            LOGGER.error(msg)
            raise HomeAssistantError(msg) from err
