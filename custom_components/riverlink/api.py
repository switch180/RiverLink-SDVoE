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
    LOGGER,
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

    async def connect(self) -> bool:
        """
        Connect to the SDVoE API server and load the API version.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            LOGGER.debug(
                "Connecting to SDVoE API at %s:%s", self._host, self._port
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
                LOGGER.info("Successfully loaded API version %s", self._api_version)
                self._connected = True
                return True
            else:
                LOGGER.error("Failed to load API version: %s", data)
                await self.disconnect()
                return False
                
        except asyncio.TimeoutError as exception:
            msg = f"Timeout connecting to {self._host}:{self._port}"
            LOGGER.error(msg)
            raise RiverLinkApiClientConnectionError(msg) from exception
        except OSError as exception:
            msg = f"Connection error: {exception}"
            LOGGER.error(msg)
            raise RiverLinkApiClientConnectionError(msg) from exception
        except Exception as exception:
            msg = f"Unexpected error during connection: {exception}"
            LOGGER.error(msg)
            raise RiverLinkApiClientError(msg) from exception

    async def disconnect(self) -> None:
        """Disconnect from the API server."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as exception:
                LOGGER.debug("Error closing connection: %s", exception)
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
            raise RiverLinkApiClientCommunicationError("Not connected")
        
        response = ""
        try:
            # Read until we have a complete JSON object
            while True:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=API_TIMEOUT,
                )
                
                if not chunk:
                    raise RiverLinkApiClientCommunicationError(
                        "Connection closed by server"
                    )
                
                response += chunk.decode("utf-8")
                
                # Try to parse JSON
                try:
                    json.loads(response)
                    break  # Valid JSON, we're done
                except json.JSONDecodeError:
                    continue  # Keep reading
                    
        except asyncio.TimeoutError as exception:
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
            raise RiverLinkApiClientCommunicationError("Not connected to API server")
        
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
                    raise RiverLinkApiClientError("No request_id in PROCESSING response")
                
                LOGGER.debug(
                    "Command returned PROCESSING, polling request %s", request_id
                )
                return await self._poll_request(request_id)
            
            return data
            
        except json.JSONDecodeError as exception:
            msg = f"Invalid JSON response: {response}"
            raise RiverLinkApiClientError(msg) from exception
        except Exception as exception:
            msg = f"Error sending command: {exception}"
            raise RiverLinkApiClientCommunicationError(msg) from exception

    async def _poll_request(
        self, request_id: int, max_attempts: int = 20
    ) -> dict[str, Any]:
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
            
            self._writer.write(f"{poll_cmd}\n".encode("utf-8"))
            await self._writer.drain()
            
            response = await self._read_response()
            data = json.loads(response)
            status = data.get("status")
            
            if status == "SUCCESS":
                LOGGER.debug("Request %s completed successfully", request_id)
                return data
            elif status == "ERROR":
                error = data.get("error", {})
                msg = f"Request {request_id} failed: {error.get('message', 'Unknown error')}"
                LOGGER.error(msg)
                raise RiverLinkApiClientError(msg)
            elif status == "PROCESSING":
                LOGGER.debug("Request %s still processing", request_id)
                continue
            else:
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
                msg = f"Failed to get devices: {error.get('message', 'Unknown error')}"
                raise RiverLinkApiClientError(msg)
            
            return response
            
        except RiverLinkApiClientCommunicationError:
            # Try to reconnect and retry once
            LOGGER.warning("Communication error, attempting to reconnect...")
            await self.disconnect()
            await self.connect()
            
            response = await self._send_command(API_GET_ALL_DEVICES)
            if response.get("status") != "SUCCESS":
                error = response.get("error", {})
                msg = f"Failed to get devices: {error.get('message', 'Unknown error')}"
                raise RiverLinkApiClientError(msg)
            
            return response
