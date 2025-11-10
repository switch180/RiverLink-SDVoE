"""RiverLinkEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DEVICE_NAME,
    ATTR_FIRMWARE_COMMENT,
    ATTR_FIRMWARE_VERSION,
    ATTR_IP_ADDRESS,
    ATTRIBUTION,
    DOMAIN,
)
from .coordinator import RiverLinkDataUpdateCoordinator


class RiverLinkEntity(CoordinatorEntity[RiverLinkDataUpdateCoordinator]):
    """Base entity for RiverLink SDVoE devices."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: RiverLinkDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this SDVoE device."""
        # Try to find device in receivers first, then transmitters
        device = self.coordinator.data.get("receivers", {}).get(self._device_id)
        is_receiver = device is not None

        if not device:
            device = self.coordinator.data.get("transmitters", {}).get(self._device_id)

        if not device:
            # Fallback if device not found
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=self._device_id,
            )

        device_name = device.get(ATTR_DEVICE_NAME, self._device_id)
        firmware_version = device.get(ATTR_FIRMWARE_VERSION, "unknown")
        firmware_comment = device.get(ATTR_FIRMWARE_COMMENT, "")
        ip_address = device.get(ATTR_IP_ADDRESS)

        # Determine model from firmware comment if available
        model = "BlueRiver Receiver" if is_receiver else "BlueRiver Transmitter"
        if firmware_comment and "BlueRiver" in firmware_comment:
            model = firmware_comment

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_name,
            manufacturer="SDVoE",
            model=model,
            sw_version=firmware_version,
        )

        # Add configuration URL if we have an IP address
        if ip_address:
            device_info["configuration_url"] = f"http://{ip_address}"

        return device_info
