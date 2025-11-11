"""Constants for RiverLink SDVoE Matrix."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "sdvoe"
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

# Stream indexes
DEFAULT_STREAM_INDEX = 0
STREAM_TYPE_STEREO_AUDIO = "STEREO_AUDIO"
STREAM_TYPE_MULTICH_AUDIO = "MULTICH_AUDIO"

# Stream/Subscription states
STATE_STREAMING = "STREAMING"
STATE_STOPPED = "STOPPED"

# Display mode constants (for video output control)
DISPLAY_MODE_GENLOCK = "genlock"
DISPLAY_MODE_GENLOCK_SCALING = "genlock_scaling"
DISPLAY_MODE_FASTSWITCH = "fastswitch"
DISPLAY_MODE_FASTSWITCH_STRETCH = "fastswitch_stretch"
DISPLAY_MODE_FASTSWITCH_CROP = "fastswitch_crop"

# Resolution presets: name → (width, height, fps)
RESOLUTION_PRESETS = {
    # Broadcast/Consumer formats (17 options)
    "720p @ 60Hz": (1280, 720, 60),
    "720p @ 50Hz": (1280, 720, 50),
    "1080p @ 60Hz": (1920, 1080, 60),
    "1080p @ 50Hz": (1920, 1080, 50),
    "1080p @ 30Hz": (1920, 1080, 30),
    "1080p @ 25Hz": (1920, 1080, 25),
    "1080p @ 24Hz": (1920, 1080, 24),
    "4K UHD @ 60Hz": (3840, 2160, 60),
    "4K UHD @ 50Hz": (3840, 2160, 50),
    "4K UHD @ 30Hz": (3840, 2160, 30),
    "4K UHD @ 25Hz": (3840, 2160, 25),
    "4K UHD @ 24Hz": (3840, 2160, 24),
    "4K Cinema @ 60Hz": (4096, 2160, 60),
    "4K Cinema @ 30Hz": (4096, 2160, 30),
    "4K Cinema @ 24Hz": (4096, 2160, 24),
    # Computer/Monitor formats (9 options)
    "1024×768 @ 60Hz": (1024, 768, 60),
    "1280×768 @ 60Hz": (1280, 768, 60),
    "1280×960 @ 60Hz": (1280, 960, 60),
    "1280×1024 @ 60Hz": (1280, 1024, 60),
    "1360×768 @ 60Hz": (1360, 768, 60),
    "1400×1050 @ 60Hz": (1400, 1050, 60),
    "1600×1200 @ 60Hz": (1600, 1200, 60),
    "1680×1050 @ 60Hz": (1680, 1050, 60),
    "1920×1200 @ 60Hz": (1920, 1200, 60),
}

# Resolution thresholds
RESOLUTION_4K_HEIGHT = 2160  # 4K UHD vertical resolution threshold

# Default values for video mode
DEFAULT_DISPLAY_MODE = DISPLAY_MODE_GENLOCK
DEFAULT_RESOLUTION_PRESET = "1080p @ 60Hz"

# Attribute keys for video mode
ATTR_DISPLAY_MODE = "display_mode"
ATTR_RESOLUTION_WIDTH = "resolution_width"
ATTR_RESOLUTION_HEIGHT = "resolution_height"
ATTR_RESOLUTION_FPS = "resolution_fps"
ATTR_RESOLUTION_PRESET = "resolution_preset"
ATTR_RESOLUTION_APPLIES = "resolution_applies"
ATTR_PENDING_RESOLUTION_PRESET = "pending_resolution_preset"
ATTR_RESOLUTION_PRESET_STATUS = "resolution_preset_status"

# Video signal attributes (from HDMI_ENCODER/HDMI_DECODER status)
ATTR_VIDEO_SIGNAL_COLOR_SPACE = "video_signal_color_space"
ATTR_VIDEO_SIGNAL_BITS_PER_PIXEL = "video_signal_bits_per_pixel"
ATTR_VIDEO_SIGNAL_SCAN_MODE = "video_signal_scan_mode"

# HDCP attributes (available on both HDMI_ENCODER and HDMI_DECODER)
ATTR_HDCP_PROTECTED = "hdcp_protected"
ATTR_HDCP_VERSION = "hdcp_version"

# Resolution preset status values
PRESET_STATUS_PENDING = "pending"  # Pending preset in genlock mode
PRESET_STATUS_APPLIED = "applied"  # Resolution is applied to device
PRESET_STATUS_STORED = "stored"  # Resolution stored but not applied
