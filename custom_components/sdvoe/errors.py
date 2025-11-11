"""Error message constants for RiverLink integration."""

# Connection errors
ERROR_NOT_CONNECTED = "Not connected to API server"
ERROR_CONNECTION_CLOSED = "Connection closed by server"
ERROR_CONNECTION_FAILED = "Failed to connect or load API version"

# API errors
ERROR_NO_REQUEST_ID = "No request_id in PROCESSING response"
ERROR_REQUEST_FAILED = "Request {request_id} failed: {message}"
ERROR_GET_DEVICES_FAILED = "Failed to get devices: {message}"

# Selection errors
ERROR_UNKNOWN_MODE = "Unknown display mode: {mode}"
ERROR_UNKNOWN_PRESET = "Unknown resolution preset: {preset}"
ERROR_TRANSMITTER_NOT_FOUND = "Transmitter '{name}' not found"
ERROR_UNKNOWN_VIDEO_MODE = "Unknown video mode: {mode}"

# Validation errors
ERROR_SCALING_MODE_REQUIRES_RESOLUTION = "Scaling modes (genlock_scaling, fastswitch) require width, height, and fps"
