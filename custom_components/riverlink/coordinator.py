"""DataUpdateCoordinator for RiverLink SDVoE Matrix."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RiverLinkApiClientError
from .const import (
    ATTR_DISPLAY_MODE,
    ATTR_HDCP_PROTECTED,
    ATTR_HDCP_VERSION,
    ATTR_PENDING_RESOLUTION_PRESET,
    ATTR_RESOLUTION_APPLIES,
    ATTR_RESOLUTION_FPS,
    ATTR_RESOLUTION_HEIGHT,
    ATTR_RESOLUTION_PRESET,
    ATTR_RESOLUTION_WIDTH,
    ATTR_SOURCE_DEVICE_ID,
    ATTR_SOURCE_DEVICE_NAME,
    ATTR_STREAM_ADDRESS,
    ATTR_STREAM_ENABLED,
    ATTR_STREAM_INDEX,
    ATTR_STREAM_STATE,
    ATTR_STREAM_TYPE,
    ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL,
    ATTR_VIDEO_SIGNAL_COLOR_SPACE,
    ATTR_VIDEO_SIGNAL_SCAN_MODE,
    DEFAULT_DISPLAY_MODE,
    DISPLAY_MODE_FASTSWITCH,
    DISPLAY_MODE_FASTSWITCH_CROP,
    DISPLAY_MODE_FASTSWITCH_STRETCH,
    DISPLAY_MODE_GENLOCK,
    DISPLAY_MODE_GENLOCK_SCALING,
    LOGGER,
    RESOLUTION_PRESETS,
)
from .errors import ERROR_GET_DEVICES_FAILED

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
            msg = ERROR_GET_DEVICES_FAILED.format(message=str(exception))
            raise UpdateFailed(msg) from exception

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
                    address = stream.get(ATTR_STREAM_ADDRESS)
                    if address and address != "0.0.0.0":  # noqa: S104 - Sentinel value, not socket binding
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

    def _extract_video_mode_config(self, device: dict[str, Any]) -> dict[str, Any]:
        """
        Extract video mode configuration using correct detection logic.

        Step 1: Check HDMI_ENCODER source to determine Genlock vs Frame Buffer
        Step 2: If Frame Buffer, check FRAME_BUFFER.display_mode for specific mode

        Returns dict with: mode, width, height, fps
        """
        nodes = device.get("nodes", [])

        # Find HDMI_ENCODER and FRAME_BUFFER nodes
        hdmi_encoder = None
        frame_buffer = None

        for node in nodes:
            if node.get("type") == "HDMI_ENCODER":
                hdmi_encoder = node
            elif node.get("type") == "FRAME_BUFFER" and node.get("index") == 0:
                frame_buffer = node

        # Default fallback values
        mode = DEFAULT_DISPLAY_MODE
        width = 1920
        height = 1080
        fps = 60

        # Get frame buffer resolution (used for all modes)
        if frame_buffer:
            fb_config = frame_buffer.get("configuration", {})
            width = fb_config.get("width", 1920)
            height = fb_config.get("height", 1080)
            fps = fb_config.get("frames_per_second", 60)

        # Determine mode from HDMI_ENCODER source
        if hdmi_encoder:
            inputs = hdmi_encoder.get("inputs", [])
            main_input = None

            for input_node in inputs:
                if input_node.get("name") == "main":
                    main_input = input_node
                    break

            if main_input:
                source = main_input.get("status", {}).get("source", {})
                ref_class = source.get("ref_class")
                ref_type = source.get("ref_type")

                # Check if using direct subscription (Genlock passthrough)
                if ref_class == "SUBSCRIPTION" and ref_type == "HDMI":
                    mode = DISPLAY_MODE_GENLOCK

                # Check if using frame buffer (Genlock Scaling or Fast Switch)
                elif ref_class == "NODE" and ref_type == "FRAME_BUFFER" and frame_buffer:
                    fb_mode = frame_buffer.get("configuration", {}).get("display_mode", "")

                    if fb_mode == "GENLOCK_SCALING":
                        mode = DISPLAY_MODE_GENLOCK_SCALING
                    elif fb_mode == "FAST_SWITCHED":
                        mode = DISPLAY_MODE_FASTSWITCH
                    elif fb_mode == "FAST_SWITCHED_STRETCH":
                        mode = DISPLAY_MODE_FASTSWITCH_STRETCH
                    elif fb_mode == "FAST_SWITCHED_CROP":
                        mode = DISPLAY_MODE_FASTSWITCH_CROP
                    else:
                        # Unknown frame buffer mode, default to fastswitch
                        mode = DISPLAY_MODE_FASTSWITCH

        return {
            "mode": mode,
            "width": width,
            "height": height,
            "fps": fps,
        }

    def _find_resolution_preset(self, width: int, height: int, fps: int) -> str:
        """Find matching resolution preset or return 'Custom'."""
        for preset_name, preset_values in RESOLUTION_PRESETS.items():
            preset_width, preset_height, preset_fps = preset_values
            if width == preset_width and height == preset_height and fps == preset_fps:
                return preset_name

        return "Custom"

    def _extract_video_signal(self, device: dict[str, Any], node_type: str = "HDMI_ENCODER") -> dict[str, Any]:
        """
        Extract video signal and HDCP information from specified node type.

        Args:
            device: Device data
            node_type: "HDMI_ENCODER" for output (receivers) or "HDMI_DECODER" for input (transmitters)

        Returns dict with: width, height, fps, color_space, bits_per_pixel, scan_mode, hdcp_protected, hdcp_version

        """
        nodes = device.get("nodes", [])

        # Find specified node type (index 0)
        for node in nodes:
            if node.get("type") == node_type and node.get("index") == 0:
                status = node.get("status", {})
                video = status.get("video", {})

                return {
                    "width": video.get("width"),
                    "height": video.get("height"),
                    "fps": video.get("frames_per_second"),
                    ATTR_VIDEO_SIGNAL_COLOR_SPACE: video.get("color_space"),
                    ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL: video.get("bits_per_pixel"),
                    ATTR_VIDEO_SIGNAL_SCAN_MODE: video.get("scan_mode"),
                    ATTR_HDCP_PROTECTED: status.get(ATTR_HDCP_PROTECTED),
                    ATTR_HDCP_VERSION: status.get(ATTR_HDCP_VERSION),
                }

        # Return empty if node not found
        return {
            "width": None,
            "height": None,
            "fps": None,
            ATTR_VIDEO_SIGNAL_COLOR_SPACE: None,
            ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL: None,
            ATTR_VIDEO_SIGNAL_SCAN_MODE: None,
            ATTR_HDCP_PROTECTED: None,
            ATTR_HDCP_VERSION: None,
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

        # Parse video mode configuration from FRAME_BUFFER and HDMI_ENCODER nodes
        video_config = self._extract_video_mode_config(device)
        mode = video_config.get("mode", DEFAULT_DISPLAY_MODE)
        width = video_config.get("width", 1920)
        height = video_config.get("height", 1080)
        fps = video_config.get("fps", 60)

        # Find matching preset or use "Custom"
        preset = self._find_resolution_preset(width, height, fps)

        # Calculate if resolution applies (not genlock passthrough)
        applies = mode != DISPLAY_MODE_GENLOCK

        # Preserve pending preset if it exists (persists across refreshes)
        old_receiver = (self.data or {}).get("receivers", {}).get(device_id, {}) if hasattr(self, "data") else {}
        pending_preset = old_receiver.get(ATTR_PENDING_RESOLUTION_PRESET)

        # Extract video signal information from HDMI_ENCODER status
        video_signal = self._extract_video_signal(device)

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
            # Video mode state (from actual device)
            ATTR_DISPLAY_MODE: mode,
            ATTR_RESOLUTION_WIDTH: width,
            ATTR_RESOLUTION_HEIGHT: height,
            ATTR_RESOLUTION_FPS: fps,
            ATTR_RESOLUTION_PRESET: preset,
            ATTR_RESOLUTION_APPLIES: applies,
            ATTR_PENDING_RESOLUTION_PRESET: pending_preset,
            # Video signal information (from HDMI_ENCODER status)
            ATTR_VIDEO_SIGNAL_COLOR_SPACE: video_signal.get(ATTR_VIDEO_SIGNAL_COLOR_SPACE),
            ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL: video_signal.get(ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL),
            ATTR_VIDEO_SIGNAL_SCAN_MODE: video_signal.get(ATTR_VIDEO_SIGNAL_SCAN_MODE),
            ATTR_HDCP_PROTECTED: video_signal.get(ATTR_HDCP_PROTECTED),
            ATTR_HDCP_VERSION: video_signal.get(ATTR_HDCP_VERSION),
        }

        # Parse subscriptions
        subscriptions = device.get("subscriptions", [])
        for sub in subscriptions:
            sub_type = sub.get("type")
            sub_config = sub.get("configuration", {})
            sub_status = sub.get("status", {})

            address = sub_config.get("address", "0.0.0.0")  # noqa: S104 - Sentinel value, not socket binding
            enabled = sub_config.get("enable", False)
            state = sub_status.get("state", "STOPPED")

            # Lookup source transmitter
            source_device_id = stream_map.get(address) if address != "0.0.0.0" else None  # noqa: S104
            source_device_name = None
            if source_device_id and source_device_id in transmitters:
                source_device_name = transmitters[source_device_id].get("device_name")

            device_data["subscriptions"].append(
                {
                    ATTR_STREAM_TYPE: sub_type,
                    ATTR_STREAM_INDEX: sub.get("index", 0),
                    ATTR_STREAM_ADDRESS: address,
                    ATTR_STREAM_ENABLED: enabled,
                    ATTR_STREAM_STATE: state,
                    ATTR_SOURCE_DEVICE_ID: source_device_id,
                    ATTR_SOURCE_DEVICE_NAME: source_device_name,
                }
            )

        return device_data

    def _parse_transmitter(self, device: dict[str, Any]) -> dict[str, Any]:
        """Parse transmitter device data."""
        device_id = device.get("device_id", "unknown")
        identity = device.get("identity", {})
        config = device.get("configuration", {})
        status = device.get("status", {})

        # Extract input signal information from HDMI_DECODER status
        input_signal = self._extract_video_signal(device, "HDMI_DECODER")

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
            # Input signal information (from HDMI_DECODER status)
            ATTR_RESOLUTION_WIDTH: input_signal.get("width"),
            ATTR_RESOLUTION_HEIGHT: input_signal.get("height"),
            ATTR_RESOLUTION_FPS: input_signal.get("fps"),
            ATTR_VIDEO_SIGNAL_COLOR_SPACE: input_signal.get(ATTR_VIDEO_SIGNAL_COLOR_SPACE),
            ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL: input_signal.get(ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL),
            ATTR_VIDEO_SIGNAL_SCAN_MODE: input_signal.get(ATTR_VIDEO_SIGNAL_SCAN_MODE),
            ATTR_HDCP_PROTECTED: input_signal.get(ATTR_HDCP_PROTECTED),
            ATTR_HDCP_VERSION: input_signal.get(ATTR_HDCP_VERSION),
        }

        # Parse streams
        streams = device.get("streams", [])
        for stream in streams:
            stream_type = stream.get("type")
            stream_config = stream.get("configuration", {})
            stream_status = stream.get("status", {})

            device_data["streams"].append(
                {
                    ATTR_STREAM_TYPE: stream_type,
                    ATTR_STREAM_INDEX: stream.get("index", 0),
                    ATTR_STREAM_ADDRESS: stream_config.get("address", "0.0.0.0"),  # noqa: S104
                    ATTR_STREAM_ENABLED: stream_config.get("enable", False),
                    ATTR_STREAM_STATE: stream_status.get("state", "STOPPED"),
                }
            )

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
