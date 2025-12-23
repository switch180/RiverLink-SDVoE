"""Error message constants for RiverLink integration."""

# Connection errors
ERROR_NOT_CONNECTED = "Not connected to API server"
ERROR_CONNECTION_CLOSED = "Connection closed by server"
ERROR_CONNECTION_FAILED = "Failed to connect or load API version"
ERROR_CONNECTION_RETRY_FAILED = "Failed to connect to {host}:{port} after {attempts} attempts: {error}"
ERROR_CONNECTION_UNEXPECTED = "Unexpected error during connection: {error}"
ERROR_CONNECTION_LOGIC = "Connection logic error (reached end of retry loop)"

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

# Join/Leave subscription errors
ERROR_JOIN_FAILED = "Failed to join subscription: {message}"
ERROR_LEAVE_FAILED = "Failed to leave subscription: {message}"

# Subscription verification errors (after retries exhausted)
ERROR_JOIN_NOT_STREAMING = (
    "Subscription {stream_type}:{index} failed to stream on {receiver_id} "
    "after {attempts} attempts"
)

ERROR_LEAVE_STILL_STREAMING = (
    "Subscription {stream_type}:{index} still streaming on {device_id} "
    "after {attempts} leave attempts"
)

# Device state query error
ERROR_GET_DEVICE_STATE_FAILED = "Failed to get device state: {message}"

# UI error messages (for HomeAssistantError)
ERROR_UI_JOIN_FAILED = "Failed to switch video source: {error}"
ERROR_UI_LEAVE_FAILED = "Failed to disconnect video source: {error}"

# Stream control errors
ERROR_START_STREAM_FAILED = (
    "Failed to start stream {stream_type}:{index} on {device_id}: {message}"
)
ERROR_STOP_STREAM_FAILED = (
    "Failed to stop stream {stream_type}:{index} on {device_id}: {message}"
)
ERROR_STREAM_NOT_FOUND = "Stream {stream_type}:{index} not found on device {device_id}"
