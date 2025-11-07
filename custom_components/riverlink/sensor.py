"""Sensor platform for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ACTIVE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_DISPLAY_MODE,
    ATTR_FIRMWARE_VERSION,
    ATTR_HDCP_PROTECTED,
    ATTR_HDCP_VERSION,
    ATTR_IP_ADDRESS,
    ATTR_RESOLUTION_APPLIES,
    ATTR_RESOLUTION_FPS,
    ATTR_RESOLUTION_HEIGHT,
    ATTR_RESOLUTION_WIDTH,
    ATTR_SOURCE_DEVICE_ID,
    ATTR_SOURCE_DEVICE_NAME,
    ATTR_STREAM_ADDRESS,
    ATTR_STREAM_ENABLED,
    ATTR_STREAM_INDEX,
    ATTR_STREAM_STATE,
    ATTR_STREAM_TYPE,
    ATTR_TEMPERATURE,
    ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL,
    ATTR_VIDEO_SIGNAL_COLOR_SPACE,
    ATTR_VIDEO_SIGNAL_SCAN_MODE,
    DEFAULT_DISPLAY_MODE,
    DISPLAY_MODE_FASTSWITCH,
    DISPLAY_MODE_FASTSWITCH_CROP,
    DISPLAY_MODE_FASTSWITCH_STRETCH,
    DISPLAY_MODE_GENLOCK,
    DISPLAY_MODE_GENLOCK_SCALING,
    DOMAIN,
    STREAM_TYPE_HDMI,
    STREAM_TYPE_HDMI_AUDIO,
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
    """Set up sensor platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = []
    
    # Create entities for all receivers
    for device_id in coordinator.data.get("receivers", {}):
        entities.extend([
            RiverLinkReceiverTemperatureSensor(coordinator, device_id),
            RiverLinkReceiverVideoSourceSensor(coordinator, device_id),
            RiverLinkReceiverAudioSourceSensor(coordinator, device_id),
            RiverLinkReceiverVideoSignalSensor(coordinator, device_id),
            RiverLinkReceiverIPAddressSensor(coordinator, device_id),
            RiverLinkReceiverFirmwareSensor(coordinator, device_id),
        ])
    
    # Create entities for all transmitters
    for device_id in coordinator.data.get("transmitters", {}):
        entities.extend([
            RiverLinkTransmitterTemperatureSensor(coordinator, device_id),
            RiverLinkTransmitterHDMIStreamSensor(coordinator, device_id),
            RiverLinkTransmitterAudioStreamSensor(coordinator, device_id),
            RiverLinkTransmitterInputSignalSensor(coordinator, device_id),
            RiverLinkTransmitterIPAddressSensor(coordinator, device_id),
            RiverLinkTransmitterFirmwareSensor(coordinator, device_id),
        ])
    
    async_add_entities(entities)


class RiverLinkReceiverTemperatureSensor(RiverLinkEntity, SensorEntity):
    """Temperature sensor for receiver."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "temperature"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if receiver:
            return receiver.get(ATTR_TEMPERATURE)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return {}
        
        return {
            ATTR_DEVICE_ID: receiver[ATTR_DEVICE_ID],
            ATTR_DEVICE_NAME: receiver[ATTR_DEVICE_NAME],
            ATTR_IP_ADDRESS: receiver.get(ATTR_IP_ADDRESS),
            ATTR_FIRMWARE_VERSION: receiver.get(ATTR_FIRMWARE_VERSION),
        }


class RiverLinkReceiverVideoSourceSensor(RiverLinkEntity, SensorEntity):
    """Video source sensor for receiver."""

    _attr_icon = "mdi:video-input-hdmi"
    _attr_translation_key = "video_source"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_video_source"

    @property
    def native_value(self) -> str | None:
        """Return the video source transmitter name."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return None
        
        # Find HDMI subscription
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI:
                return sub.get(ATTR_SOURCE_DEVICE_NAME) or "Unknown"
        
        return "No Source"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return {}
        
        # Find HDMI subscription
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI:
                return {
                    ATTR_SOURCE_DEVICE_ID: sub.get(ATTR_SOURCE_DEVICE_ID),
                    ATTR_SOURCE_DEVICE_NAME: sub.get(ATTR_SOURCE_DEVICE_NAME),
                    ATTR_STREAM_ADDRESS: sub.get(ATTR_STREAM_ADDRESS),
                    ATTR_STREAM_STATE: sub.get(ATTR_STREAM_STATE),
                    ATTR_STREAM_ENABLED: sub.get(ATTR_STREAM_ENABLED),
                    ATTR_STREAM_INDEX: sub.get(ATTR_STREAM_INDEX),
                }
        
        return {}


class RiverLinkReceiverAudioSourceSensor(RiverLinkEntity, SensorEntity):
    """Audio source sensor for receiver."""

    _attr_icon = "mdi:volume-high"
    _attr_translation_key = "audio_source"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_audio_source"

    @property
    def native_value(self) -> str | None:
        """Return the audio source transmitter name."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return None
        
        # Find HDMI_AUDIO subscription
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI_AUDIO:
                return sub.get(ATTR_SOURCE_DEVICE_NAME) or "Unknown"
        
        return "No Source"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return {}
        
        # Find HDMI_AUDIO subscription
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI_AUDIO:
                return {
                    ATTR_SOURCE_DEVICE_ID: sub.get(ATTR_SOURCE_DEVICE_ID),
                    ATTR_SOURCE_DEVICE_NAME: sub.get(ATTR_SOURCE_DEVICE_NAME),
                    ATTR_STREAM_ADDRESS: sub.get(ATTR_STREAM_ADDRESS),
                    ATTR_STREAM_STATE: sub.get(ATTR_STREAM_STATE),
                    ATTR_STREAM_ENABLED: sub.get(ATTR_STREAM_ENABLED),
                    ATTR_STREAM_INDEX: sub.get(ATTR_STREAM_INDEX),
                }
        
        return {}


class RiverLinkReceiverVideoSignalSensor(RiverLinkEntity, SensorEntity):
    """Video signal information sensor for receiver."""

    _attr_icon = "mdi:video-box"
    _attr_translation_key = "video_signal"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_video_signal"

    @property
    def native_value(self) -> str | None:
        """Return formatted video signal with color space."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return None
        
        width = receiver.get(ATTR_RESOLUTION_WIDTH, 0)
        height = receiver.get(ATTR_RESOLUTION_HEIGHT, 0)
        fps = receiver.get(ATTR_RESOLUTION_FPS, 0)
        color_space = receiver.get(ATTR_VIDEO_SIGNAL_COLOR_SPACE, '')
        bpp = receiver.get(ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL, 0)
        
        return f"{width}×{height} @ {fps}Hz, {color_space} {bpp}-bit"

    @property
    def extra_state_attributes(self) -> dict:
        """Return video signal and HDCP attributes."""
        receiver = self.coordinator.data["receivers"].get(self._device_id, {})
        
        return {
            ATTR_RESOLUTION_WIDTH: receiver.get(ATTR_RESOLUTION_WIDTH),
            ATTR_RESOLUTION_HEIGHT: receiver.get(ATTR_RESOLUTION_HEIGHT),
            ATTR_RESOLUTION_FPS: receiver.get(ATTR_RESOLUTION_FPS),
            ATTR_VIDEO_SIGNAL_COLOR_SPACE: receiver.get(ATTR_VIDEO_SIGNAL_COLOR_SPACE),
            ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL: receiver.get(ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL),
            ATTR_VIDEO_SIGNAL_SCAN_MODE: receiver.get(ATTR_VIDEO_SIGNAL_SCAN_MODE),
            ATTR_HDCP_PROTECTED: receiver.get(ATTR_HDCP_PROTECTED),
            ATTR_HDCP_VERSION: receiver.get(ATTR_HDCP_VERSION),
        }


class RiverLinkReceiverIPAddressSensor(RiverLinkEntity, SensorEntity):
    """IP address sensor for receiver."""

    _attr_icon = "mdi:ip-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "ip_address"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_ip_address"

    @property
    def native_value(self) -> str | None:
        """Return the IP address."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if receiver:
            return receiver.get(ATTR_IP_ADDRESS)
        return None


class RiverLinkReceiverFirmwareSensor(RiverLinkEntity, SensorEntity):
    """Firmware version sensor for receiver."""

    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "firmware_version"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_firmware"

    @property
    def native_value(self) -> str | None:
        """Return the firmware version."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if receiver:
            return receiver.get(ATTR_FIRMWARE_VERSION)
        return None


# Transmitter sensors


class RiverLinkTransmitterTemperatureSensor(RiverLinkEntity, SensorEntity):
    """Temperature sensor for transmitter."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "temperature"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if transmitter:
            return transmitter.get(ATTR_TEMPERATURE)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if not transmitter:
            return {}
        
        return {
            ATTR_DEVICE_ID: transmitter[ATTR_DEVICE_ID],
            ATTR_DEVICE_NAME: transmitter[ATTR_DEVICE_NAME],
            ATTR_IP_ADDRESS: transmitter.get(ATTR_IP_ADDRESS),
            ATTR_FIRMWARE_VERSION: transmitter.get(ATTR_FIRMWARE_VERSION),
        }


class RiverLinkTransmitterHDMIStreamSensor(RiverLinkEntity, SensorEntity):
    """HDMI stream state sensor for transmitter."""

    _attr_icon = "mdi:video-wireless"

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        device = coordinator.data["transmitters"][device_id]
        device_name = device[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{device_id}_hdmi_stream"
        self._attr_name = f"{device_name} HDMI Stream"
        self.entity_id = f"sensor.riverlink_{device_name.lower().replace(' ', '_').replace('-', '_')}_hdmi_stream"

    @property
    def native_value(self) -> str | None:
        """Return the HDMI stream state."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if not transmitter:
            return None
        
        # Find HDMI stream
        for stream in transmitter.get("streams", []):
            if stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI:
                return stream.get(ATTR_STREAM_STATE, "STOPPED")
        
        return "STOPPED"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if not transmitter:
            return {}
        
        # Find HDMI stream
        for stream in transmitter.get("streams", []):
            if stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI:
                return {
                    ATTR_STREAM_TYPE: stream.get(ATTR_STREAM_TYPE),
                    ATTR_STREAM_INDEX: stream.get(ATTR_STREAM_INDEX),
                    ATTR_STREAM_ADDRESS: stream.get(ATTR_STREAM_ADDRESS),
                    ATTR_STREAM_ENABLED: stream.get(ATTR_STREAM_ENABLED),
                }
        
        return {}


class RiverLinkTransmitterAudioStreamSensor(RiverLinkEntity, SensorEntity):
    """Audio stream state sensor for transmitter."""

    _attr_icon = "mdi:broadcast"

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        device = coordinator.data["transmitters"][device_id]
        device_name = device[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{device_id}_audio_stream"
        self._attr_name = f"{device_name} Audio Stream"
        self.entity_id = f"sensor.riverlink_{device_name.lower().replace(' ', '_').replace('-', '_')}_audio_stream"

    @property
    def native_value(self) -> str | None:
        """Return the audio stream state."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if not transmitter:
            return None
        
        # Find HDMI_AUDIO stream
        for stream in transmitter.get("streams", []):
            if stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI_AUDIO:
                return stream.get(ATTR_STREAM_STATE, "STOPPED")
        
        return "STOPPED"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if not transmitter:
            return {}
        
        # Find HDMI_AUDIO stream
        for stream in transmitter.get("streams", []):
            if stream.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI_AUDIO:
                return {
                    ATTR_STREAM_TYPE: stream.get(ATTR_STREAM_TYPE),
                    ATTR_STREAM_INDEX: stream.get(ATTR_STREAM_INDEX),
                    ATTR_STREAM_ADDRESS: stream.get(ATTR_STREAM_ADDRESS),
                    ATTR_STREAM_ENABLED: stream.get(ATTR_STREAM_ENABLED),
                }
        
        return {}


class RiverLinkTransmitterInputSignalSensor(RiverLinkEntity, SensorEntity):
    """Input signal information sensor for transmitter."""

    _attr_icon = "mdi:video-input-hdmi"
    _attr_translation_key = "input_signal"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_input_signal"

    @property
    def native_value(self) -> str | None:
        """Return formatted input signal with color space."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if not transmitter:
            return None
        
        width = transmitter.get(ATTR_RESOLUTION_WIDTH, 0)
        height = transmitter.get(ATTR_RESOLUTION_HEIGHT, 0)
        fps = transmitter.get(ATTR_RESOLUTION_FPS, 0)
        color_space = transmitter.get(ATTR_VIDEO_SIGNAL_COLOR_SPACE, '')
        bpp = transmitter.get(ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL, 0)
        
        return f"{width}×{height} @ {fps}Hz, {color_space} {bpp}-bit"

    @property
    def extra_state_attributes(self) -> dict:
        """Return input signal and HDCP attributes."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id, {})
        
        return {
            ATTR_RESOLUTION_WIDTH: transmitter.get(ATTR_RESOLUTION_WIDTH),
            ATTR_RESOLUTION_HEIGHT: transmitter.get(ATTR_RESOLUTION_HEIGHT),
            ATTR_RESOLUTION_FPS: transmitter.get(ATTR_RESOLUTION_FPS),
            ATTR_VIDEO_SIGNAL_COLOR_SPACE: transmitter.get(ATTR_VIDEO_SIGNAL_COLOR_SPACE),
            ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL: transmitter.get(ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL),
            ATTR_VIDEO_SIGNAL_SCAN_MODE: transmitter.get(ATTR_VIDEO_SIGNAL_SCAN_MODE),
            ATTR_HDCP_PROTECTED: transmitter.get(ATTR_HDCP_PROTECTED),
            ATTR_HDCP_VERSION: transmitter.get(ATTR_HDCP_VERSION),
        }


class RiverLinkTransmitterIPAddressSensor(RiverLinkEntity, SensorEntity):
    """IP address sensor for transmitter."""

    _attr_icon = "mdi:ip-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "ip_address"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_ip_address"

    @property
    def native_value(self) -> str | None:
        """Return the IP address."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if transmitter:
            return transmitter.get(ATTR_IP_ADDRESS)
        return None


class RiverLinkTransmitterFirmwareSensor(RiverLinkEntity, SensorEntity):
    """Firmware version sensor for transmitter."""

    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "firmware_version"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_firmware"

    @property
    def native_value(self) -> str | None:
        """Return the firmware version."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if transmitter:
            return transmitter.get(ATTR_FIRMWARE_VERSION)
        return None
