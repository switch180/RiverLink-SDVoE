"""Constants for RiverLink SDVoE Matrix."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "riverlink"
ATTRIBUTION = "Tool developed by switch180 on GitHub: https://github.com/switch180"

# Configuration keys
CONF_API_VERSION = "api_version"

# Default values
DEFAULT_HOST = "10.0.1.135"
DEFAULT_PORT = 6970
DEFAULT_API_VERSION = "2.13.0.0"
DEFAULT_SCAN_INTERVAL = 5  # seconds

# API constants
API_TIMEOUT = 10  # seconds
API_REQUIRE_COMMAND = "require blueriver_api"
API_GET_ALL_DEVICES = "get all device"
API_REQUEST_COMMAND = "request"

# Device attributes
ATTR_DEVICE_ID = "device_id"
ATTR_DEVICE_NAME = "device_name"
ATTR_IP_ADDRESS = "ip_address"
ATTR_ACTIVE = "active"
ATTR_TEMPERATURE = "temperature"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_FIRMWARE_COMMENT = "firmware_comment"
ATTR_IS_RECEIVER = "is_receiver"
ATTR_IS_TRANSMITTER = "is_transmitter"

# Stream/Subscription attributes
ATTR_STREAM_TYPE = "stream_type"
ATTR_STREAM_STATE = "stream_state"
ATTR_STREAM_ADDRESS = "stream_address"
ATTR_STREAM_INDEX = "stream_index"
ATTR_STREAM_ENABLED = "stream_enabled"
ATTR_SOURCE_DEVICE_ID = "source_device_id"
ATTR_SOURCE_DEVICE_NAME = "source_device_name"
ATTR_SUBSCRIPTION_INDEX = "subscription_index"

# Stream types
STREAM_TYPE_HDMI = "HDMI"
STREAM_TYPE_HDMI_AUDIO = "HDMI_AUDIO"
STREAM_TYPE_AUDIO = "AUDIO"
STREAM_TYPE_STEREO_AUDIO = "STEREO_AUDIO"
STREAM_TYPE_MULTICH_AUDIO = "MULTICH_AUDIO"

# Stream/Subscription states
STATE_STREAMING = "STREAMING"
STATE_STOPPED = "STOPPED"
