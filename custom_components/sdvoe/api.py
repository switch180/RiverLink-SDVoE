"""API Client for RiverLink SDVoE Matrix."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .const import (
    API_GET_ALL_DEVICES,
    API_REQUEST_COMMAND,
    API_REQUIRE_COMMAND,
    API_TIMEOUT,
    CONNECT_RETRY_INITIAL_DELAY,
    CONNECT_RETRY_MAX_DELAY,
    LOGGER,
    MAX_CONNECT_RETRIES_SETUP,
)
from .errors import (
    ERROR_CONNECTION_CLOSED,
    ERROR_CONNECTION_LOGIC,
    ERROR_CONNECTION_RETRY_FAILED,
    ERROR_CONNECTION_UNEXPECTED,
    ERROR_GET_DEVICES_FAILED,
    ERROR_NO_REQUEST_ID,
    ERROR_NOT_CONNECTED,
    ERROR_SCALING_MODE_REQUIRES_RESOLUTION,
    ERROR_UNKNOWN_VIDEO_MODE,
)


class RiverLinkApiClientError(Exception):
    """Exception to indicate a general API error."""


class RiverLinkApiClientCommunicationError(RiverLinkApiClientError):
    """Exception to indicate a communication error."""


class RiverLinkApiClientConnectionError(RiverLinkApiClientError):
    """Exception to indicate a connection error."""


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

        Uses asyncio.Lock to serialize all socket operations and prevent
        concurrent access that could cause command interleaving or response
        mismatches when multiple devices switch sources simultaneously.

        Args:
            command: Text command to send (without newline).

        Returns:
            JSON response dict.

        """
        if not self.is_connected:
            raise RiverLinkApiClientCommunicationError(ERROR_NOT_CONNECTED)

        async with self._lock:  # Serialize all socket operations
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

    async def async_join_subscription(
        self,
        transmitter_id: str,
        receiver_id: str,
        stream_type: str = "HDMI",
        tx_index: int = 0,
        rx_index: int = 0,
    ) -> dict[str, Any]:
        """
        Join transmitter stream to receiver subscription.

        Audio (HDMI_AUDIO) automatically follows HDMI join.

        Args:
            transmitter_id: Transmitter device ID
            receiver_id: Receiver device ID
            stream_type: Stream type (default: HDMI)
            tx_index: Transmitter stream index (default: 0)
            rx_index: Receiver subscription index (default: 0)

        Returns:
            API response dict

        """
        if not self.is_connected:
            await self.connect()

        command = f"join {transmitter_id}:{stream_type}:{tx_index} {receiver_id}:{stream_type}:{rx_index}"
        response = await self._send_command(command)

        if response.get("status") != "SUCCESS":
            error = response.get("error", {})
            msg = f"Failed to join subscription: {error.get('message', 'Unknown error')}"
            raise RiverLinkApiClientError(msg)

        return response

    async def async_leave_subscription(
        self,
        device_id: str,
        stream_type: str = "HDMI",
        index: int = 0,
    ) -> dict[str, Any]:
        """
        Leave a subscription.

        Audio (HDMI_AUDIO) automatically stops when leaving HDMI.

        Args:
            device_id: Receiver device ID
            stream_type: Stream type (default: HDMI)
            index: Subscription index (default: 0)

        Returns:
            API response dict

        """
        if not self.is_connected:
            await self.connect()

        command = f"leave {device_id}:{stream_type}:{index}"
        response = await self._send_command(command)

        if response.get("status") != "SUCCESS":
            error = response.get("error", {})
            msg = f"Failed to leave subscription: {error.get('message', 'Unknown error')}"
            raise RiverLinkApiClientError(msg)

        return response

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
