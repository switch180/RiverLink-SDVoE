"""Binary sensor platform for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ACTIVE,
    ATTR_DEVICE_NAME,
    ATTR_STREAM_STATE,
    ATTR_STREAM_TYPE,
    STATE_STREAMING,
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
    """Set up binary sensor platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BinarySensorEntity] = []
    
    # Create entities for all receivers
    for device_id in coordinator.data.get("receivers", {}):
        entities.extend([
            RiverLinkReceiverOnlineSensor(coordinator, device_id),
            RiverLinkReceiverVideoStreamingSensor(coordinator, device_id),
            RiverLinkReceiverAudioStreamingSensor(coordinator, device_id),
        ])
    
    # Create entities for all transmitters
    for device_id in coordinator.data.get("transmitters", {}):
        entities.append(
            RiverLinkTransmitterOnlineSensor(coordinator, device_id)
        )
    
    async_add_entities(entities)


class RiverLinkReceiverOnlineSensor(RiverLinkEntity, BinarySensorEntity):
    """Online/offline status for receiver."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        device = coordinator.data["receivers"][device_id]
        device_name = device[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{device_id}_online"
        self._attr_name = f"{device_name} Online"
        self.entity_id = f"binary_sensor.riverlink_{device_name.lower().replace(' ', '_').replace('-', '_')}_online"

    @property
    def is_on(self) -> bool:
        """Return true if device is online."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if receiver:
            return receiver.get(ATTR_ACTIVE, False)
        return False


class RiverLinkReceiverVideoStreamingSensor(RiverLinkEntity, BinarySensorEntity):
    """Video streaming status for receiver."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:video"

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        device = coordinator.data["receivers"][device_id]
        device_name = device[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{device_id}_video_streaming"
        self._attr_name = f"{device_name} Video Streaming"
        self.entity_id = f"binary_sensor.riverlink_{device_name.lower().replace(' ', '_').replace('-', '_')}_video_streaming"

    @property
    def is_on(self) -> bool:
        """Return true if video is streaming."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return False
        
        # Check if HDMI subscription is streaming
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI:
                return sub.get(ATTR_STREAM_STATE) == STATE_STREAMING
        
        return False


class RiverLinkReceiverAudioStreamingSensor(RiverLinkEntity, BinarySensorEntity):
    """Audio streaming status for receiver."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:speaker"

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        device = coordinator.data["receivers"][device_id]
        device_name = device[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{device_id}_audio_streaming"
        self._attr_name = f"{device_name} Audio Streaming"
        self.entity_id = f"binary_sensor.riverlink_{device_name.lower().replace(' ', '_').replace('-', '_')}_audio_streaming"

    @property
    def is_on(self) -> bool:
        """Return true if audio is streaming."""
        receiver = self.coordinator.data["receivers"].get(self._device_id)
        if not receiver:
            return False
        
        # Check if HDMI_AUDIO subscription is streaming
        for sub in receiver.get("subscriptions", []):
            if sub.get(ATTR_STREAM_TYPE) == STREAM_TYPE_HDMI_AUDIO:
                return sub.get(ATTR_STREAM_STATE) == STATE_STREAMING
        
        return False


class RiverLinkTransmitterOnlineSensor(RiverLinkEntity, BinarySensorEntity):
    """Online/offline status for transmitter."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        device = coordinator.data["transmitters"][device_id]
        device_name = device[ATTR_DEVICE_NAME]
        
        self._attr_unique_id = f"{device_id}_online"
        self._attr_name = f"{device_name} Online"
        self.entity_id = f"binary_sensor.riverlink_{device_name.lower().replace(' ', '_').replace('-', '_')}_online"

    @property
    def is_on(self) -> bool:
        """Return true if device is online."""
        transmitter = self.coordinator.data["transmitters"].get(self._device_id)
        if transmitter:
            return transmitter.get(ATTR_ACTIVE, False)
        return False
