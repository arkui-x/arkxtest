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
ArkUI-X device abstraction.

An ArkUIXDevice can be passed to UiDriver(device) just like a HarmonyOS Device,
so existing test scripts work without modification.

Usage:
    from hypium.uidriver.arkuix.arkuix_device import ArkUIXDevice
    device = ArkUIXDevice("127.0.0.1", 8017, "ios")
    driver = UiDriver(device)
"""

from hypium.uidriver.arkuix.socket_client import DEFAULT_PORT

class ArkUIXDevice:
    """
    Represents an ArkUI-X cross-platform device connection (iOS / Android).

    This object holds the socket connection parameters and can be passed
    to UiDriver() as a drop-in replacement for a HarmonyOS Device object.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT,
                 platform: str = "ios", **kwargs):
        """
        Args:
            host: Device IP or 127.0.0.1 (with iproxy/adb forward)
            port: Socket server port (default 8017)
            platform: "ios" or "android"
            kwargs: Optional: connect_timeout, recv_timeout, display_width, display_height
        """
        self.host = host
        self.port = port
        self.platform = platform
        self.device_sn = f"{platform}:{host}:{port}"
        self.extra = kwargs
