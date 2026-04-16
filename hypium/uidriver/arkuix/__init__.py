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
Hypium ArkUI-X cross-platform driver via socket protocol.
Supports both iOS and Android ArkUI-X applications through the same
UiTestSocketServer embedded in the app.
"""

from hypium.uidriver.arkuix.arkuix_driver import ArkUIXDriver
from hypium.uidriver.arkuix.socket_client import ArkUIXSocketClient
from hypium.uidriver.arkuix.arkuix_device import ArkUIXDevice
from hypium.uidriver.arkuix.arkuix_driver_impl import ArkUIXDriverImpl

__all__ = ["ArkUIXDriver", "ArkUIXSocketClient", "ArkUIXDevice", "ArkUIXDriverImpl"]
