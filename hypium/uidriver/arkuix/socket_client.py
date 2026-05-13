# Copyright (c) 2026 Huawei Device Co., Ltd.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Socket client for communicating with ArkUI-X UiTestSocketServer.
Works identically for iOS and Android ArkUI-X applications.

Protocol (matches C++ test_socket_server.cpp / socket_protocol.cpp):
  - TCP socket connection
  - Each message: 4-byte big-endian total-length header + JSON payload
    (total-length = HEADER_SIZE + payload_size, i.e. header value includes itself)
  - Request:  {"command": <int>, "params": {...}}
    - Response: {"command": <int>, "result": <value>, "err_code": 0, "err_mes": ""}
"""

import json
import socket
import struct
import time
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger("hypium.arkuix")

# Default port matching C++ SOCKET_DEFAULT_PORT in socket_protocol.h
DEFAULT_PORT = 8017
HEADER_SIZE = 4
# Max message size matching C++ SOCKET_TOTAL_SIZE (includes header)
MAX_MESSAGE_SIZE = 1024 * 1024
RECV_BUFFER_SIZE = 64 * 1024
CONNECT_TIMEOUT = 10.0
RECV_TIMEOUT = 60.0


class ArkUIXSocketError(Exception):
    """Base exception for ArkUI-X socket communication errors."""
    pass


class ArkUIXConnectionError(ArkUIXSocketError):
    """Raised when connection to the ArkUI-X socket server fails."""
    pass


class ArkUIXProtocolError(ArkUIXSocketError):
    """Raised for protocol-level errors (malformed response, etc.)."""
    pass


class ArkUIXCommandError(ArkUIXSocketError):
    """Raised when the server returns an error for a command."""

    def __init__(self, code: Any, message: str):
        self.code = code
        self.error_message = message
        super().__init__(f"[{code}] {message}")


class ArkUIXSocketClient:
    """
    TCP socket client that speaks the ArkUI-X UiTest JSON protocol.
    Platform-agnostic: works for both iOS and Android ArkUI-X apps.

    Usage:
        client = ArkUIXSocketClient("192.168.1.100", 8017)
        client.connect()
        result = client.send_command(106, {"x": 100, "y": 200})
        client.disconnect()
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT,
                 connect_timeout: float = CONNECT_TIMEOUT,
                 recv_timeout: float = RECV_TIMEOUT):
        self._host = host
        self._port = port
        self._connect_timeout = connect_timeout
        self._recv_timeout = recv_timeout
        self._sock: Optional[socket.socket] = None
        self._connected = False

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_connected(self) -> bool:
        return self._connected and self._sock is not None

    def connect(self, retry_times: int = 3, retry_interval: float = 1.0):
        """Establish TCP connection to the ArkUI-X socket server."""
        last_err = None
        for attempt in range(retry_times):
            try:
                self._do_connect()
                logger.info(f"Connected to ArkUI-X server at {self._host}:{self._port}")
                return
            except Exception as e:
                last_err = e
                logger.warning(f"Connection attempt {attempt + 1}/{retry_times} failed: {e}")
                if attempt < retry_times - 1:
                    time.sleep(retry_interval)

        raise ArkUIXConnectionError(
            f"Failed to connect to {self._host}:{self._port} after {retry_times} attempts: {last_err}"
        )

    def _do_connect(self):
        """Internal: create socket and connect."""
        self.disconnect()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self._connect_timeout)
        try:
            sock.connect((self._host, self._port))
        except (socket.error, OSError) as e:
            sock.close()
            raise ArkUIXConnectionError(f"Socket connect failed: {e}") from e

        sock.settimeout(self._recv_timeout)
        self._sock = sock
        self._connected = True

    def disconnect(self):
        """Close the TCP connection."""
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._connected = False

    def send_command(self, command: int, params: Optional[Dict[str, Any]] = None,
                     timeout: float = None) -> Any:
        """
        Send a command to the ArkUI-X server and return the result.

        Args:
            command: Integer command code (e.g., 106 for DRIVER_CLICK)
            params: Command parameters dict
            timeout: Optional per-command recv timeout override

        Returns:
            The "result" field from the server response

        Raises:
            ArkUIXConnectionError: Not connected
            ArkUIXProtocolError: Protocol/parsing error
            ArkUIXCommandError: Server returned an error
        """
        if not self.is_connected:
            raise ArkUIXConnectionError("Not connected to ArkUI-X server")

        request = {"command": command}
        if params:
            request["params"] = params

        request_json = json.dumps(request, ensure_ascii=False, separators=(',', ':'))
        logger.debug(f">>> [cmd={command}] {request_json[:200]}")

        old_timeout = None
        if timeout is not None:
            old_timeout = self._sock.gettimeout()
            self._sock.settimeout(timeout)

        try:
            self._send_message(request_json)
            response_json = self._recv_message()
        except socket.timeout as e:
            raise ArkUIXProtocolError(f"Timeout waiting for response to command {command}") from e
        except (socket.error, OSError) as e:
            self._connected = False
            raise ArkUIXConnectionError(f"Connection lost during command {command}: {e}") from e
        finally:
            if old_timeout is not None and self._sock is not None:
                try:
                    self._sock.settimeout(old_timeout)
                except (socket.error, OSError) as e:
                    logger.warning(f"Failed to restore socket timeout: {e} (socket may be closed by other thread)")

        logger.debug(f"<<< [cmd={command}] {response_json[:200]}")

        # Parse response
        try:
            response = json.loads(response_json)
        except json.JSONDecodeError as e:
            raise ArkUIXProtocolError(f"Invalid JSON response: {e}") from e

        if not isinstance(response, dict):
            raise ArkUIXProtocolError(f"Invalid response type: {type(response).__name__}")

        response_command = response.get("command")
        if response_command is None:
            raise ArkUIXProtocolError("Response missing 'command' field")
        if response_command != command:
            raise ArkUIXProtocolError(
                f"Mismatched response command: expected {command}, got {response_command}"
            )

        err_code = response.get("err_code", 0)
        err_mes = response.get("err_mes", "")
        try:
            err_code_is_success = int(err_code) == 0
        except (TypeError, ValueError):
            err_code_is_success = False

        if not err_code_is_success:
            raise ArkUIXCommandError(err_code, str(err_mes or "Unknown error"))

        # Server response format: {"command": <int>, "result": <value>, "err_code": 0, "err_mes": ""}
        result = response.get("result")

        # Legacy compatibility: server may still send error strings in result.
        if isinstance(result, str) and result.startswith("ERROR:"):
            raise ArkUIXCommandError(-1, result)

        return result

    def _send_message(self, message: str):
        """Send a length-prefixed message over the socket.

        Protocol: 4-byte big-endian header containing total size
        (HEADER_SIZE + payload_size), followed by UTF-8 JSON payload.
        """
        data = message.encode("utf-8")
        total_size = HEADER_SIZE + len(data)
        if total_size > MAX_MESSAGE_SIZE:
            raise ArkUIXProtocolError(f"Message too large: {total_size} bytes (max {MAX_MESSAGE_SIZE})")

        # 4-byte big-endian total length header (includes header itself)
        header = struct.pack(">I", total_size)
        self._sock.sendall(header + data)

    def _recv_message(self) -> str:
        """Receive a length-prefixed message from the socket.

        Protocol: 4-byte big-endian header = total size (including header),
        then (total_size - HEADER_SIZE) bytes of payload.
        """
        # Read 4-byte header
        header = self._recv_exact(HEADER_SIZE)
        total_size = struct.unpack(">I", header)[0]

        if total_size <= HEADER_SIZE or total_size > MAX_MESSAGE_SIZE:
            raise ArkUIXProtocolError(f"Invalid message total size: {total_size}")

        # Read payload (total_size minus header)
        payload_len = total_size - HEADER_SIZE
        data = self._recv_exact(payload_len)
        return data.decode("utf-8")

    def _recv_exact(self, nbytes: int) -> bytes:
        """Read exactly nbytes from the socket."""
        buf = bytearray()
        while len(buf) < nbytes:
            chunk = self._sock.recv(min(nbytes - len(buf), RECV_BUFFER_SIZE))
            if not chunk:
                self._connected = False
                raise ArkUIXConnectionError("Connection closed by remote")
            buf.extend(chunk)
        return bytes(buf)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def __del__(self):
        self.disconnect()
