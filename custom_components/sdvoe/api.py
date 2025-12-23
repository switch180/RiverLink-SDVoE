"""API Client for RiverLink SDVoE Matrix."""

from __future__ import annotations

import asyncio
import functools
import json
from typing import Any

from .const import (
    API_GET_ALL_DEVICES,
    API_REQUEST_COMMAND,
    API_REQUIRE_COMMAND,
    API_START_STREAM,
    API_STOP_STREAM,
    API_TIMEOUT,
    CONNECT_RETRY_INITIAL_DELAY,
    CONNECT_RETRY_MAX_DELAY,
    DEFAULT_STREAM_INDEX,
    LOGGER,
    MAX_CONNECT_RETRIES_SETUP,
    MAX_JOIN_RETRIES,
    MAX_LEAVE_RETRIES,
    STATE_STREAMING,
    VERIFY_RETRY_INITIAL_DELAY,
    VERIFY_RETRY_MAX_DELAY,
)
from .errors import (
    ERROR_CONNECTION_CLOSED,
    ERROR_CONNECTION_LOGIC,
    ERROR_CONNECTION_RETRY_FAILED,
    ERROR_CONNECTION_UNEXPECTED,
    ERROR_GET_DEVICE_STATE_FAILED,
    ERROR_GET_DEVICES_FAILED,
    ERROR_JOIN_FAILED,
    ERROR_JOIN_NOT_STREAMING,
    ERROR_LEAVE_FAILED,
    ERROR_LEAVE_STILL_STREAMING,
    ERROR_NO_REQUEST_ID,
    ERROR_NOT_CONNECTED,
    ERROR_SCALING_MODE_REQUIRES_RESOLUTION,
    ERROR_START_STREAM_FAILED,
    ERROR_STOP_STREAM_FAILED,
    ERROR_UNKNOWN_VIDEO_MODE,
)


class RiverLinkApiClientError(Exception):
    """Exception to indicate a general API error."""


class RiverLinkApiClientCommunicationError(RiverLinkApiClientError):
    """Exception to indicate a communication error."""


class RiverLinkApiClientConnectionError(RiverLinkApiClientError):
    """Exception to indicate a connection error."""


def with_lock(func: Any) -> Any:
    """
    Serialize API operations using asyncio.Lock.

    Ensures that public API methods (join, leave, set_video_mode, etc.)
    hold the lock for their entire execution, including command sending
    and PROCESSING status polling. This prevents race conditions when
    multiple operations are called in quick succession.
    """
    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            return await func(self, *args, **kwargs)
    return wrapper


class RiverLinkApiClient:
    """API Client for SDVoE Matrix using raw TCP socket."""

    def __init__(
        self,
        host: str,
        port: int,
        api_version: str,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._api_version = api_version
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._lock = asyncio.Lock()  # Serialize command execution to prevent concurrent socket access

    async def connect(
        self,
        max_retries: int = MAX_CONNECT_RETRIES_SETUP,
        initial_delay: float = CONNECT_RETRY_INITIAL_DELAY,
        max_delay: float = CONNECT_RETRY_MAX_DELAY,
    ) -> bool:
        """
        Connect to the SDVoE API server with retry logic.

        Args:
            max_retries: Maximum connection attempts (default from const)
            initial_delay: Initial retry delay in seconds (default from const)
            max_delay: Maximum retry delay in seconds (default from const)

        Returns:
            True if connection successful

        Raises:
            RiverLinkApiClientConnectionError: If all retries fail

        """
        delay = initial_delay
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                LOGGER.debug(
                    "Connecting to SDVoE API at %s:%s (attempt %s/%s)",
                    self._host,
                    self._port,
                    attempt,
                    max_retries,
                )

                # Open TCP connection
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=API_TIMEOUT,
                )

                # Send require command to load API
                require_cmd = f"{API_REQUIRE_COMMAND} {self._api_version}\n"
                LOGGER.debug("Sending require command: %s", require_cmd.strip())

                self._writer.write(require_cmd.encode("utf-8"))
                await self._writer.drain()

                # Read response
                response = await self._read_response()
                data = json.loads(response)

                if data.get("status") == "SUCCESS":
                    LOGGER.info("Successfully connected to BlueRiver add-on")
                    self._connected = True
                    return True

                # API rejected connection
                LOGGER.error("API rejected connection: %s", data)
                await self.disconnect()
                return False

            except (TimeoutError, OSError, ConnectionRefusedError) as exception:
                last_error = exception

                # Connection failed - retry?
                if attempt < max_retries:
                    LOGGER.info(
                        "Connection attempt %s/%s failed: %s. "
                        "Retrying in %.1f seconds... "
                        "(BlueRiver add-on may still be starting up)",
                        attempt,
                        max_retries,
                        exception,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    # Exponential backoff with cap
                    delay = min(delay * 1.5, max_delay)
                else:
                    # All retries exhausted
                    msg = ERROR_CONNECTION_RETRY_FAILED.format(
                        host=self._host,
                        port=self._port,
                        attempts=max_retries,
                        error=exception,
                    )
                    LOGGER.error(msg)
                    raise RiverLinkApiClientConnectionError(msg) from last_error

            except Exception as exception:
                # Unexpected error - don't retry
                msg = ERROR_CONNECTION_UNEXPECTED.format(error=exception)
                LOGGER.error(msg)
                raise RiverLinkApiClientError(msg) from exception

        # Should never reach here
        raise RiverLinkApiClientError(ERROR_CONNECTION_LOGIC)

    async def disconnect(self) -> None:
        """Disconnect from the API server."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except OSError as exception:
                LOGGER.error("OS error closing connection: %s", exception)
            except Exception as exception:  # noqa: BLE001 - Final catch-all for cleanup
                LOGGER.error("Unexpected error closing connection: %s", exception)
            finally:
                self._writer = None
                self._reader = None
                self._connected = False
                LOGGER.debug("Disconnected from SDVoE API")

    @property
    def is_connected(self) -> bool:
        """Return True if connected to the API server."""
        return self._connected and self._writer is not None

    async def _read_response(self) -> str:
        """
        Read a complete JSON response from the socket.

        Returns:
            JSON response string.

        """
        if not self._reader:
            raise RiverLinkApiClientCommunicationError(ERROR_NOT_CONNECTED)

        response = ""
        try:
            # Read until we have a complete JSON object
            while True:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=API_TIMEOUT,
                )

                if not chunk:
                    raise RiverLinkApiClientCommunicationError(ERROR_CONNECTION_CLOSED)

                response += chunk.decode("utf-8")

                # Try to parse JSON
                try:
                    json.loads(response)
                    break  # Valid JSON, we're done
                except json.JSONDecodeError:
                    continue  # Keep reading

        except TimeoutError as exception:
            msg = "Timeout reading response"
            raise RiverLinkApiClientCommunicationError(msg) from exception

        return response

    async def _send_command(self, command: str) -> dict[str, Any]:
        """
        Send a text command to the API and return the JSON response.

        Handles PROCESSING status by polling with request command.

        Args:
            command: Text command to send (without newline).

        Returns:
            JSON response dict.

        """
        if not self.is_connected:
            raise RiverLinkApiClientCommunicationError(ERROR_NOT_CONNECTED)

        try:
            # Send command
            cmd_str = command + "\n"
            LOGGER.debug("Sending command: %s", command)

            self._writer.write(cmd_str.encode("utf-8"))
            await self._writer.drain()

            # Read response
            response = await self._read_response()
            data = json.loads(response)

            # Handle PROCESSING status with polling
            if data.get("status") == "PROCESSING":
                request_id = data.get("request_id")
                if not request_id:
                    raise RiverLinkApiClientError(ERROR_NO_REQUEST_ID)  # noqa: TRY301

                LOGGER.debug("Command returned PROCESSING, polling request %s", request_id)
                return await self._poll_request(request_id)
            return data

        except json.JSONDecodeError as exception:
            msg = f"Invalid JSON response: {response}"
            raise RiverLinkApiClientError(msg) from exception
        except Exception as exception:
            msg = f"Error sending command: {exception}"
            raise RiverLinkApiClientCommunicationError(msg) from exception

    async def _poll_request(self, request_id: int, max_attempts: int = 20) -> dict[str, Any]:
        """
        Poll for request completion.

        Args:
            request_id: The request ID to poll.
            max_attempts: Maximum number of polling attempts.

        Returns:
            Final JSON response dict.

        """
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(0.5)  # Wait before polling

            poll_cmd = f"{API_REQUEST_COMMAND} {request_id}"
            LOGGER.debug("Polling request %s (attempt %s)", request_id, attempt)

            self._writer.write(f"{poll_cmd}\n".encode())
            await self._writer.drain()

            response = await self._read_response()
            data = json.loads(response)
            status = data.get("status")

            if status == "SUCCESS":
                LOGGER.debug("Request %s completed successfully", request_id)
                return data
            if status == "ERROR":
                error = data.get("error", {})
                msg = f"Request {request_id} failed: {error.get('message', 'Unknown error')}"
                LOGGER.error(msg)
                raise RiverLinkApiClientError(msg)
            if status == "PROCESSING":
                LOGGER.debug("Request %s still processing", request_id)
                continue
            msg = f"Unknown status '{status}' for request {request_id}"
            raise RiverLinkApiClientError(msg)

        msg = f"Request {request_id} timed out after {max_attempts} attempts"
        raise RiverLinkApiClientCommunicationError(msg)

    async def _get_device_state_internal(self, device_id: str) -> dict[str, Any]:
        """
        Get device state (internal, no lock).

        Uses command: get DEVICE_ID device

        MUST be called from within a @with_lock method.

        Args:
            device_id: Device ID to query

        Returns:
            API response with device data

        Raises:
            RiverLinkApiClientError: If command fails

        """
        command = f"get {device_id} device"
        response = await self._send_command(command)

        if response.get("status") != "SUCCESS":
            error = response.get("error", {})
            msg = ERROR_GET_DEVICE_STATE_FAILED.format(
                message=error.get("message", "Unknown error")
            )
            raise RiverLinkApiClientError(msg)

        return response

    @with_lock
    async def async_get_device_state(self, device_id: str) -> dict[str, Any]:
        """
        Get current state for a specific device (public, locked).

        For external callers who need device state.

        Args:
            device_id: Device ID to query

        Returns:
            API response with device data

        """
        return await self._get_device_state_internal(device_id)

    def _is_subscription_streaming(
        self,
        device_data: dict,
        stream_type: str,
        stream_index: int,
    ) -> bool:
        """
        Check if subscription is STREAMING.

        Args:
            device_data: Parsed device response from get command
            stream_type: "HDMI" or "HDMI_AUDIO"
            stream_index: Subscription index to check

        Returns:
            True if subscription[type, index].status.state == "STREAMING"

        """
        result = device_data.get("result", {})
        devices = result.get("devices", [])

        # Get first device from array (single device query)
        if not devices:
            return False
        device = devices[0]

        subscriptions = device.get("subscriptions", [])

        for sub in subscriptions:
            if (sub.get("type") == stream_type and
                sub.get("index") == stream_index):
                status = sub.get("status", {})
                state = status.get("state", "STOPPED")
                return state == STATE_STREAMING

        return False

    @with_lock
    async def async_get_data(self) -> dict[str, Any]:
        """
        Get data from all devices in the SDVoE network.

        Returns:
            Parsed device data dict.

        """
        if not self.is_connected:
            await self.connect()

        try:
            response = await self._send_command(API_GET_ALL_DEVICES)

            if response.get("status") != "SUCCESS":
                error = response.get("error", {})
                msg = ERROR_GET_DEVICES_FAILED.format(message=error.get("message", "Unknown error"))
                raise RiverLinkApiClientError(msg)
            return response

        except RiverLinkApiClientCommunicationError as err:
            # Try to reconnect and retry once
            LOGGER.warning("Communication error, attempting to reconnect...")
            await self.disconnect()
            await self.connect()

            response = await self._send_command(API_GET_ALL_DEVICES)
            if response.get("status") != "SUCCESS":
                error = response.get("error", {})
                msg = ERROR_GET_DEVICES_FAILED.format(message=error.get("message", "Unknown error"))
                raise RiverLinkApiClientError(msg) from err
            return response

    @with_lock
    async def async_join_subscription(
        self,
        transmitter_id: str,
        receiver_id: str,
        stream_type: str = "HDMI",
        tx_index: int = DEFAULT_STREAM_INDEX,
        rx_index: int = DEFAULT_STREAM_INDEX,
    ) -> dict[str, Any]:
        """
        Join subscription with retry-until-streaming verification.

        Workaround for hardware bug where join returns SUCCESS
        but stream doesn't start. Retries until verified STREAMING.

        Args:
            transmitter_id: Transmitter device ID
            receiver_id: Receiver device ID
            stream_type: Stream type (default: HDMI)
            tx_index: Transmitter stream index (default: DEFAULT_STREAM_INDEX)
            rx_index: Receiver subscription index (default: DEFAULT_STREAM_INDEX)

        Returns:
            API response dict

        Raises:
            RiverLinkApiClientError: If join fails or verification fails after retries

        """
        if not self.is_connected:
            await self.connect()

        command = f"join {transmitter_id}:{stream_type}:{tx_index} {receiver_id}:{stream_type}:{rx_index}"
        delay = VERIFY_RETRY_INITIAL_DELAY

        for attempt in range(1, MAX_JOIN_RETRIES + 1):
            LOGGER.debug(
                "Join attempt %d/%d: %s:%s:%d → %s:%s:%d",
                attempt,
                MAX_JOIN_RETRIES,
                transmitter_id,
                stream_type,
                tx_index,
                receiver_id,
                stream_type,
                rx_index,
            )

            # Send join command
            response = await self._send_command(command)

            if response.get("status") != "SUCCESS":
                error = response.get("error", {})
                msg = ERROR_JOIN_FAILED.format(
                    message=error.get("message", "Unknown error")
                )
                raise RiverLinkApiClientError(msg)

            # Verify streaming state
            device_response = await self._get_device_state_internal(receiver_id)

            if self._is_subscription_streaming(device_response, stream_type, rx_index):
                LOGGER.debug(
                    "Verified %s:%d streaming on %s (attempt %d)",
                    stream_type,
                    rx_index,
                    receiver_id,
                    attempt,
                )
                return response

            # Not streaming yet - wait before retry (debug only, expected behavior)
            if attempt < MAX_JOIN_RETRIES:
                LOGGER.debug(
                    "%s:%d not streaming on %s yet, waiting %.1fs before retry %d/%d",
                    stream_type,
                    rx_index,
                    receiver_id,
                    delay,
                    attempt,
                    MAX_JOIN_RETRIES,
                )
                await asyncio.sleep(delay)
                # Exponential backoff with cap
                delay = min(delay * 2, VERIFY_RETRY_MAX_DELAY)

        # All retries exhausted - dump device state for debugging and raise exception
        LOGGER.debug(
            "Join verification failed after %d attempts. Final device state: %s",
            MAX_JOIN_RETRIES,
            json.dumps(device_response),
        )
        msg = ERROR_JOIN_NOT_STREAMING.format(
            stream_type=stream_type,
            index=rx_index,
            receiver_id=receiver_id,
            attempts=MAX_JOIN_RETRIES,
        )
        raise RiverLinkApiClientError(msg)

    @with_lock
    async def async_leave_subscription(
        self,
        device_id: str,
        stream_type: str = "HDMI",
        index: int = DEFAULT_STREAM_INDEX,
    ) -> dict[str, Any]:
        """
        Leave subscription with verification.

        Verifies that stream actually stops. Retries if needed.

        Args:
            device_id: Receiver device ID
            stream_type: Stream type (default: HDMI)
            index: Subscription index (default: DEFAULT_STREAM_INDEX)

        Returns:
            API response dict

        Raises:
            RiverLinkApiClientError: If leave fails or verification fails after retries

        """
        if not self.is_connected:
            await self.connect()

        command = f"leave {device_id}:{stream_type}:{index}"
        delay = VERIFY_RETRY_INITIAL_DELAY

        for attempt in range(1, MAX_LEAVE_RETRIES + 1):
            LOGGER.debug(
                "Leave attempt %d/%d: %s:%s:%d",
                attempt,
                MAX_LEAVE_RETRIES,
                device_id,
                stream_type,
                index,
            )

            # Send leave command
            response = await self._send_command(command)

            if response.get("status") != "SUCCESS":
                error = response.get("error", {})
                msg = ERROR_LEAVE_FAILED.format(
                    message=error.get("message", "Unknown error")
                )
                raise RiverLinkApiClientError(msg)

            # Verify stopped
            device_response = await self._get_device_state_internal(device_id)

            if not self._is_subscription_streaming(device_response, stream_type, index):
                LOGGER.debug(
                    "Verified %s:%d stopped on %s",
                    stream_type,
                    index,
                    device_id,
                )
                return response

            # Still streaming - wait before retry
            if attempt < MAX_LEAVE_RETRIES:
                LOGGER.debug(
                    "%s:%d still streaming on %s, waiting %.1fs before retry %d/%d",
                    stream_type,
                    index,
                    device_id,
                    delay,
                    attempt,
                    MAX_LEAVE_RETRIES,
                )
                await asyncio.sleep(delay)
                # Exponential backoff with cap
                delay = min(delay * 2, VERIFY_RETRY_MAX_DELAY)

        # All retries exhausted - dump device state for debugging and raise exception
        LOGGER.debug(
            "Leave verification failed after %d attempts. Final device state: %s",
            MAX_LEAVE_RETRIES,
            json.dumps(device_response),
        )
        msg = ERROR_LEAVE_STILL_STREAMING.format(
            stream_type=stream_type,
            index=index,
            device_id=device_id,
            attempts=MAX_LEAVE_RETRIES,
        )
        raise RiverLinkApiClientError(msg)

    @with_lock
    async def async_set_video_mode(
        self,
        device_id: str,
        mode: str,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
    ) -> dict[str, Any]:
        """
        Set video output mode and optional resolution.

        Args:
            device_id: Device ID (receiver)
            mode: Display mode - one of:
                - "genlock" (no resolution needed)
                - "genlock_scaling" (requires resolution)
                - "fastswitch" (requires resolution, keep aspect)
                - "fastswitch_stretch" (requires resolution)
                - "fastswitch_crop" (requires resolution)
            width: Video width in pixels (required except for genlock)
            height: Video height in pixels (required except for genlock)
            fps: Frame rate (required except for genlock)

        Returns:
            API response dict

        Raises:
            ValueError: If resolution params missing for modes that need them
            RiverLinkApiClientError: If API call fails

        """
        if not self.is_connected:
            await self.connect()

        # Build command based on mode
        if mode == "genlock":
            # Genlock doesn't need resolution
            command = f"set {device_id} video genlock"

        elif mode == "genlock_scaling":
            # Genlock scaling requires resolution
            if width is None or height is None or fps is None:
                raise ValueError(ERROR_SCALING_MODE_REQUIRES_RESOLUTION)
            command = f"set {device_id} video genlock_scaling size {width} {height} fps {fps}"

        elif mode == "fastswitch":
            # Fast switch (keep aspect) requires resolution
            if width is None or height is None or fps is None:
                raise ValueError(ERROR_SCALING_MODE_REQUIRES_RESOLUTION)
            command = f"set {device_id} video fastswitch size {width} {height} fps {fps}"

        elif mode == "fastswitch_stretch":
            # Fast switch stretch requires resolution
            if width is None or height is None or fps is None:
                raise ValueError(ERROR_SCALING_MODE_REQUIRES_RESOLUTION)
            command = f"set {device_id} video fastswitch stretch size {width} {height} fps {fps}"

        elif mode == "fastswitch_crop":
            # Fast switch crop requires resolution
            if width is None or height is None or fps is None:
                raise ValueError(ERROR_SCALING_MODE_REQUIRES_RESOLUTION)
            command = f"set {device_id} video fastswitch crop size {width} {height} fps {fps}"

        else:
            msg = ERROR_UNKNOWN_VIDEO_MODE.format(mode=mode)
            raise ValueError(msg)

        LOGGER.info("Setting video mode for %s: %s", device_id, command)

        # Send command
        response = await self._send_command(command)

        if response.get("status") != "SUCCESS":
            error = response.get("error", {})
            msg = f"Failed to set video mode: {error.get('message', 'Unknown error')}"
            raise RiverLinkApiClientError(msg)

        return response

    @with_lock
    async def async_start_stream(
        self,
        device_id: str,
        stream_type: str = "HDMI",
        stream_index: int = DEFAULT_STREAM_INDEX,
    ) -> dict[str, Any]:
        """
        Start a transmitter stream.

        Command format: start {device_id}:{stream_type}:{stream_index}
        Example: start f82285014a66:HDMI:0

        Args:
            device_id: Transmitter device ID
            stream_type: Stream type (default: HDMI)
            stream_index: Stream index (default: DEFAULT_STREAM_INDEX)

        Returns:
            API response dict

        Raises:
            RiverLinkApiClientError: If command fails

        """
        if not self.is_connected:
            await self.connect()

        command = f"{API_START_STREAM} {device_id}:{stream_type}:{stream_index}"
        LOGGER.debug("Starting stream: %s", command)

        response = await self._send_command(command)

        if response.get("status") != "SUCCESS":
            error = response.get("error", {})
            msg = ERROR_START_STREAM_FAILED.format(
                stream_type=stream_type,
                index=stream_index,
                device_id=device_id,
                message=error.get("message", "Unknown error"),
            )
            raise RiverLinkApiClientError(msg)

        LOGGER.info(
            "Successfully started stream %s:%s:%d",
            device_id,
            stream_type,
            stream_index,
        )
        return response

    @with_lock
    async def async_stop_stream(
        self,
        device_id: str,
        stream_type: str = "HDMI",
        stream_index: int = DEFAULT_STREAM_INDEX,
    ) -> dict[str, Any]:
        """
        Stop a transmitter stream.

        Command format: stop {device_id}:{stream_type}:{stream_index}
        Example: stop f82285014a66:HDMI:0

        Args:
            device_id: Transmitter device ID
            stream_type: Stream type (default: HDMI)
            stream_index: Stream index (default: DEFAULT_STREAM_INDEX)

        Returns:
            API response dict

        Raises:
            RiverLinkApiClientError: If command fails

        """
        if not self.is_connected:
            await self.connect()

        command = f"{API_STOP_STREAM} {device_id}:{stream_type}:{stream_index}"
        LOGGER.debug("Stopping stream: %s", command)

        response = await self._send_command(command)

        if response.get("status") != "SUCCESS":
            error = response.get("error", {})
            msg = ERROR_STOP_STREAM_FAILED.format(
                stream_type=stream_type,
                index=stream_index,
                device_id=device_id,
                message=error.get("message", "Unknown error"),
            )
            raise RiverLinkApiClientError(msg)

        LOGGER.info(
            "Successfully stopped stream %s:%s:%d",
            device_id,
            stream_type,
            stream_index,
        )
        return response
