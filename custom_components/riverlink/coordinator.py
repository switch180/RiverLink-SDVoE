"""DataUpdateCoordinator for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RiverLinkApiClientError
from .const import LOGGER

if TYPE_CHECKING:
    from .data import RiverLinkConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class RiverLinkDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: RiverLinkConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and parse data from the API."""
        try:
            # Get raw API response
            response = await self.config_entry.runtime_data.client.async_get_data()
            
            # Parse device data
            return self._parse_device_data(response)
            
        except RiverLinkApiClientError as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}") from exception

    def _parse_device_data(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw API response into structured device data.
        
        Returns dict with:
            - receivers: {device_id: device_data}
            - transmitters: {device_id: device_data}
            - stream_map: {multicast_address: transmitter_device_id}
        """
        result = response.get("result", {})
        devices = result.get("devices", [])
        
        receivers = {}
        transmitters = {}
        stream_map = {}  # multicast address -> transmitter device_id
        
        # First pass: Build transmitter data and stream map
        for device in devices:
            identity = device.get("identity", {})
            
            if identity.get("is_transmitter"):
                device_id = device.get("device_id")
                transmitter_data = self._parse_transmitter(device)
                transmitters[device_id] = transmitter_data
                
                # Build stream map from transmitter streams
                for stream in transmitter_data.get("streams", []):
                    address = stream.get("address")
                    if address and address != "0.0.0.0":
                        stream_map[address] = device_id
        
        # Second pass: Build receiver data with source lookups
        for device in devices:
            identity = device.get("identity", {})
            
            if identity.get("is_receiver"):
                device_id = device.get("device_id")
                receivers[device_id] = self._parse_receiver(device, stream_map, transmitters)
        
        LOGGER.debug(
            "Parsed %d receivers and %d transmitters",
            len(receivers),
            len(transmitters),
        )
        
        return {
            "receivers": receivers,
            "transmitters": transmitters,
            "stream_map": stream_map,
        }

    def _parse_receiver(
        self,
        device: dict[str, Any],
        stream_map: dict[str, str],
        transmitters: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse receiver device data."""
        device_id = device.get("device_id", "unknown")
        identity = device.get("identity", {})
        config = device.get("configuration", {})
        status = device.get("status", {})
        
        # Extract basic device info
        device_data = {
            "device_id": device_id,
            "device_name": config.get("device_name", device_id),
            "ip_address": self._extract_ip_address(device),
            "active": status.get("active", False),
            "temperature": status.get("temperature"),
            "firmware_version": identity.get("firmware_version", "unknown"),
            "firmware_comment": identity.get("firmware_comment", ""),
            "subscriptions": [],
        }
        
        # Parse subscriptions
        subscriptions = device.get("subscriptions", [])
        for sub in subscriptions:
            sub_type = sub.get("type")
            sub_config = sub.get("configuration", {})
            sub_status = sub.get("status", {})
            
            address = sub_config.get("address", "0.0.0.0")
            enabled = sub_config.get("enable", False)
            state = sub_status.get("state", "STOPPED")
            
            # Lookup source transmitter
            source_device_id = stream_map.get(address) if address != "0.0.0.0" else None
            source_device_name = None
            if source_device_id and source_device_id in transmitters:
                source_device_name = transmitters[source_device_id].get("device_name")
            
            device_data["subscriptions"].append({
                "type": sub_type,
                "index": sub.get("index", 0),
                "address": address,
                "enabled": enabled,
                "state": state,
                "source_device_id": source_device_id,
                "source_device_name": source_device_name,
            })
        
        return device_data

    def _parse_transmitter(self, device: dict[str, Any]) -> dict[str, Any]:
        """Parse transmitter device data."""
        device_id = device.get("device_id", "unknown")
        identity = device.get("identity", {})
        config = device.get("configuration", {})
        status = device.get("status", {})
        
        # Extract basic device info
        device_data = {
            "device_id": device_id,
            "device_name": config.get("device_name", device_id),
            "ip_address": self._extract_ip_address(device),
            "active": status.get("active", False),
            "temperature": status.get("temperature"),
            "firmware_version": identity.get("firmware_version", "unknown"),
            "firmware_comment": identity.get("firmware_comment", ""),
            "streams": [],
        }
        
        # Parse streams
        streams = device.get("streams", [])
        for stream in streams:
            stream_type = stream.get("type")
            stream_config = stream.get("configuration", {})
            stream_status = stream.get("status", {})
            
            device_data["streams"].append({
                "type": stream_type,
                "index": stream.get("index", 0),
                "address": stream_config.get("address", "0.0.0.0"),
                "enabled": stream_config.get("enable", False),
                "state": stream_status.get("state", "STOPPED"),
            })
        
        return device_data

    def _extract_ip_address(self, device: dict[str, Any]) -> str | None:
        """Extract IP address from device nodes."""
        nodes = device.get("nodes", [])
        for node in nodes:
            if node.get("type") == "NETWORK_INTERFACE":
                node_status = node.get("status", {})
                ip_info = node_status.get("ip", {})
                return ip_info.get("address")
        return None
