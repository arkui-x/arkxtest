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
ArkUI-X cross-platform UI test driver.

Connects to the UiTestSocketServer embedded in ArkUI-X applications
(both iOS and Android) via TCP socket, and provides the same driver
interface as OHOSDriver for test script compatibility.

Architecture:
    Python (ArkUIXDriver)
        └── TCP socket ──→  ArkUI-X App
                              └── UiTestSocketServer (C++)
                                   └── SocketDispatcher
                                        └── Driver (click/swipe/find...)

Usage:
    from hypium.uidriver.arkuix import ArkUIXDriver

    # Connect to an ArkUI-X app on iOS simulator / real device
    driver = ArkUIXDriver("192.168.1.100", port=8017, platform="ios")
    driver.connect()

    # Same API as OHOSDriver
    driver.click((100, 200))
    component = driver.find_component({"text": "确认"})
    driver.swipe("UP", distance=40)

    driver.close()
"""

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import logging
import random
from typing import List, Optional, Any, Tuple
from urllib.parse import urlparse

from hypium.uidriver.arkuix.socket_client import (
    ArkUIXSocketClient,
    DEFAULT_PORT,
)
from hypium.uidriver.arkuix.arkuix_component import ArkUIXComponent, SocketCommand
from hypium.uidriver.by import By
from hypium.model.basic_data_type import Rect, DisplayRotation
from hypium.exception import HypiumNotSupportError, HypiumOperationFailError

logger = logging.getLogger("hypium.arkuix")

# Direction constants matching C++ UiDirection enum & hypium UiParam
DIRECTION_MAP = {
    "LEFT": 0,
    "RIGHT": 1,
    "UP": 2,
    "DOWN": 3,
}


def _on_dict_from_selector(selector) -> dict:
    """
    Convert a BY selector or a plain dict to the JSON dict expected by C++ ReadOnObject.

    Supports:
      - dict: pass through (e.g. {"text": "hello", "type": "Button"})
      - BY object: walk the _sourcing_call chain to extract all conditions
      - ArkUIXComponent: return by componentId (for scroll_search etc.)
    """
    if isinstance(selector, dict):
        return selector

    # BY selector: walk the _sourcing_call chain to collect all conditions
    # Each BY node has _sourcing_call = (parent_by, 'By.method', [value])
    # The chain ends when parent is the seed (By#seed) or has no _sourcing_call
    on = {}
    # Mapping from BY method names to C++ server JSON keys
    method_to_key = {
        "key": "componentId",     # BY.key() → componentId on server
        "id": "componentId",      # BY.id() → componentId on server
        "text": "text",
        "type": "type",
        "clickable": "clickable",
        "longClickable": "longClickable",
        "scrollable": "scrollable",
        "enabled": "enabled",
        "focused": "focused",
        "selected": "selected",
        "checked": "checked",
        "checkable": "checkable",
        "isBefore": "isBefore",
        "isAfter": "isAfter",
        "within": "within",
    }

    current = selector
    while current is not None:
        sc = getattr(current, '_sourcing_call', None)
        if sc is None:
            break
        parent, method_name, args = sc
        method = method_name.split('.')[-1]  # 'By.key' -> 'key'
        if args and method in method_to_key:
            json_key = method_to_key[method]
            value = args[0]
            # Recursively convert nested BY selectors (isBefore/isAfter/within)
            if method in ("isBefore", "isAfter", "within") and not isinstance(value, dict):
                value = _on_dict_from_selector(value)
            on[json_key] = value

            # BY.text("xxx", MatchPattern.STARTS_WITH) -> {"text": "xxx", "matchPattern": 2}
            if method == "text" and len(args) > 1:
                match_pattern = args[1]
                if hasattr(match_pattern, "value"):
                    match_pattern = match_pattern.value
                on["matchPattern"] = match_pattern
        # Walk up to parent
        if hasattr(parent, '_sourcing_call') and parent._sourcing_call is not None:
            parent_sc = parent._sourcing_call
            if parent_sc[0] is not parent:  # avoid infinite loop at seed
                current = parent
                continue
        break

    return on


class ArkUIXDriver:
    """
    ArkUI-X cross-platform UI test driver.
    Supports both iOS and Android ArkUI-X apps via the same socket protocol.
    """

    # Platform constants
    PLATFORM_IOS = "ios"
    PLATFORM_ANDROID = "android"

    @staticmethod
    def _is_selector_target(target) -> bool:
        return isinstance(target, dict) or isinstance(target, By)

    @staticmethod
    def _raise_invalid_ui_target(target):
        raise RuntimeError(f"invalid Ui Operation target {type(target).__name__}")

    @staticmethod
    def _raise_component_not_found():
        raise RuntimeError("Can't find component")

    def __init__(self, host: str, port: int = DEFAULT_PORT,
                 platform: str = "ios",
                 connect_timeout: float = 10.0,
                 recv_timeout: float = 60.0,
                 device_id: str = None):
        """
        Args:
            host: IP address / hostname of the device running the ArkUI-X app.
                  For iOS simulator use "127.0.0.1"; for real device use its IP.
                  For Android, after `adb forward tcp:8017 tcp:8017`, use "127.0.0.1".
            port: Socket server port (default 8017, matching C++ SOCKET_DEFAULT_PORT)
            platform: "ios" or "android" — affects platform-specific behaviors
            connect_timeout: TCP connect timeout in seconds
            recv_timeout: Default recv timeout per command in seconds
            device_id: Device UDID used for iOS launch / foreground commands
        """
        self._host = host
        self._port = port
        self._platform = platform.lower()
        self._device_id = device_id
        self._client = ArkUIXSocketClient(host, port, connect_timeout, recv_timeout)
        self._display_size = None  # cached (width, height)
        self._iproxy_process = None
        self._adb_forward_active = False

    # ==================== Connection lifecycle ====================

    def connect(self, retry_times: int = 3, retry_interval: float = 1.0):
        """
        连接到设备上运行的 ArkUI-X 应用内嵌的 UiTestSocketServer。

        iOS 真机: 确保 PC 和 iOS 设备在同一网络，使用设备 IP
        iOS 模拟器: 使用 127.0.0.1
        Android: 先执行 adb forward tcp:8017 tcp:8017，然后使用 127.0.0.1
        """
        self._prepare_usb_tunnel()
        self._client.connect(retry_times, retry_interval)
        logger.info(f"ArkUIXDriver connected [{self._platform}] {self._host}:{self._port}")

    def close(self):
        """断开与设备的连接"""
        self._client.disconnect()
        self._teardown_usb_tunnel()
        logger.info("ArkUIXDriver disconnected")

    def _is_local_host(self) -> bool:
        return self._host in ("127.0.0.1", "localhost")

    def _prepare_usb_tunnel(self):
        if not self._is_local_host():
            return
        if self._platform == self.PLATFORM_IOS:
            self._start_iproxy()
        elif self._platform == self.PLATFORM_ANDROID:
            self._start_adb_forward()

    def _teardown_usb_tunnel(self):
        self._stop_iproxy()
        self._stop_adb_forward()

    def _start_iproxy(self):
        if self._iproxy_process is not None and self._iproxy_process.poll() is None:
            return
        try:
            subprocess.run(
                ["pkill", "-f", f"iproxy .*{self._port}:{self._port}"],
                capture_output=True,
                timeout=3,
            )
            time.sleep(0.3)
        except Exception:
            pass

        cmd = ["iproxy"]
        if self._device_id:
            cmd.extend(["-u", self._device_id])
        cmd.append(f"{self._port}:{self._port}")

        logger.info(f"[ArkUIX] starting iproxy: {' '.join(cmd)}")
        try:
            self._iproxy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(1)
            if self._iproxy_process.poll() is not None:
                stderr = (self._iproxy_process.stderr.read() or "").strip()
                logger.warning(f"[ArkUIX] iproxy exited early. stderr: {stderr or 'empty'}")
                self._iproxy_process = None
        except FileNotFoundError:
            logger.warning("[ArkUIX] iproxy not found, please install libimobiledevice")
        except Exception as e:
            logger.warning(f"[ArkUIX] failed to start iproxy: {e}")
            self._iproxy_process = None

    def _stop_iproxy(self):
        if self._iproxy_process is not None and self._iproxy_process.poll() is None:
            logger.info("[ArkUIX] stopping iproxy")
            self._iproxy_process.terminate()
            try:
                self._iproxy_process.wait(timeout=3)
            except Exception:
                self._iproxy_process.kill()
        self._iproxy_process = None

    def _start_adb_forward(self):
        import shutil
        import subprocess

        if self._adb_forward_active:
            return
        if shutil.which("adb") is None:
            logger.warning("[ArkUIX] adb not found, skip Android USB port forwarding")
            return

        cmd = ["adb"]
        if self._device_id:
            cmd.extend(["-s", self._device_id])
        cmd.extend(["forward", f"tcp:{self._port}", f"tcp:{self._port}"])
        logger.info(f"[ArkUIX] starting adb forward: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except Exception as e:
            logger.warning(f"[ArkUIX] failed to start adb forward: {e}")
            return

        if result.returncode != 0:
            stderr = result.stderr.strip()
            logger.warning(f"[ArkUIX] adb forward failed: {stderr or result.stdout.strip()}")
            return
        self._adb_forward_active = True

    def _stop_adb_forward(self):
        import shutil
        import subprocess

        if not self._adb_forward_active or shutil.which("adb") is None:
            self._adb_forward_active = False
            return

        cmd = ["adb"]
        if self._device_id:
            cmd.extend(["-s", self._device_id])
        cmd.extend(["forward", "--remove", f"tcp:{self._port}"])
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except Exception:
            pass
        self._adb_forward_active = False

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    @property
    def platform(self) -> str:
        """返回平台标识: 'ios' 或 'android'"""
        return self._platform

    @property
    def device_sn(self) -> str:
        """返回设备标识"""
        return f"{self._platform}:{self._host}:{self._port}"

    # ==================== Low-level command ====================

    def send_command(self, command: int, params: dict = None, timeout: float = None) -> Any:
        """直接发送命令到 ArkUI-X socket server"""
        return self._client.send_command(command, params, timeout)

    # ==================== Click operations ====================

    @staticmethod
    def _normalize_click_offset(offset) -> Tuple[float, float]:
        """Normalize click offset to a 2-number tuple.

        Supported forms:
          - None: defaults to center (0.5, 0.5)
          - number: treated as (number, number)
          - 2-item tuple/list: (ox, oy)
        """
        if offset is None:
            return 0.5, 0.5

        if isinstance(offset, (int, float)):
            value = float(offset)
            return value, value

        if isinstance(offset, (tuple, list)) and len(offset) == 2:
            ox, oy = offset
            if isinstance(ox, (int, float)) and isinstance(oy, (int, float)):
                return float(ox), float(oy)

        raise ValueError("offset must be None, number, or a 2-item tuple/list")

    def click(self, target, offset=None):
        """
        点击操作。
        @param target: 坐标 tuple (x, y)，BY 选择器，或 ArkUIXComponent
        @param offset: 相对偏移 (ox, oy)，仅对控件/选择器目标有效
        """
        if isinstance(target, tuple):
            x, y = self._to_abs_pos(*target)
        else:
            if isinstance(target, ArkUIXComponent):
                comp = target
            else:
                if not self._is_selector_target(target):
                    self._raise_invalid_ui_target(target)
                comp = self.find_component(target)
                if comp is None:
                    self._raise_component_not_found()

            offset = self._normalize_click_offset(offset)

            bounds = self.get_component_property(comp, "bounds")
            width, height = bounds.get_size()
            x = bounds.left + int(width * offset[0]) if (offset[0] <= 1) else bounds.left + offset[0]
            y = bounds.top + int(height * offset[1]) if (offset[1] <= 1) else bounds.top + offset[1]

        self._client.send_command(SocketCommand.DRIVER_CLICK, {"x": int(x), "y": int(y)})

    def double_click(self, target, offset=None):
        """双击操作"""
        if isinstance(target, tuple):
            x, y = self._to_abs_pos(*target)
        else:
            if isinstance(target, ArkUIXComponent):
                comp = target
            else:
                if not self._is_selector_target(target):
                    self._raise_invalid_ui_target(target)
                comp = self.find_component(target)
                if comp is None:
                    self._raise_component_not_found()

            offset = self._normalize_click_offset(offset)

            bounds = self.get_component_property(comp, "bounds")
            width, height = bounds.get_size()
            x = bounds.left + int(width * offset[0]) if (offset[0] <= 1) else bounds.left + offset[0]
            y = bounds.top + int(height * offset[1]) if (offset[1] <= 1) else bounds.top + offset[1]

        self._client.send_command(SocketCommand.DRIVER_DOUBLE_CLICK, {"x": int(x), "y": int(y)})

    def long_click(self, target, press_time: float = 2.0, offset=None):
        """长按操作"""
        import time as _time
        logger.debug("long_click called, target=%r, type=%s", target, type(target).__name__)
        t0 = _time.time()
        if isinstance(target, tuple):
            x, y = self._to_abs_pos(*target)
        else:
            if isinstance(target, ArkUIXComponent):
                comp = target
            else:
                if not self._is_selector_target(target):
                    self._raise_invalid_ui_target(target)
                comp = self.find_component(target)
                if comp is None:
                    self._raise_component_not_found()

            offset = self._normalize_click_offset(offset)

            bounds = self.get_component_property(comp, "bounds")
            width, height = bounds.get_size()
            x = bounds.left + int(width * offset[0]) if (offset[0] <= 1) else bounds.left + offset[0]
            y = bounds.top + int(height * offset[1]) if (offset[1] <= 1) else bounds.top + offset[1]

        self._client.send_command(SocketCommand.DRIVER_LONG_CLICK, {"x": int(x), "y": int(y)})
        elapsed = _time.time() - t0
        logger.debug("long_click completed in %.3fs", elapsed)

    def touch(self, target, mode: str = "normal", scroll_target=None,
              wait_time: float = 0.1, offset=None):
        """
        通用点击操作，兼容 OHOSDriver.touch 接口。
        @param target: 坐标 tuple / BY 选择器 / ArkUIXComponent
        @param mode: "normal" / "long" / "double"
        @param scroll_target: 可滚动控件中搜索目标后点击
        @param wait_time: 点击后等待时间
        @param offset: 相对偏移
        """
        if mode not in ("normal", "long", "double"):
            raise RuntimeError("invalid touch")

        actual_target = target
        # Resolve component if scroll_target is given
        if scroll_target is not None and not isinstance(target, (tuple, ArkUIXComponent)):
            scroll_comp = self.find_component(scroll_target)
            if scroll_comp is not None:
                on_dict = _on_dict_from_selector(target)
                comp = scroll_comp.scroll_search(on_dict)
                if comp is not None:
                    actual_target = comp
                    self.wait(0.5)
                else:
                    self._raise_component_not_found()
            else:
                self._raise_component_not_found()

        if mode == "long":
            self.long_click(actual_target, offset=offset)
        elif mode == "double":
            self.double_click(actual_target, offset=offset)
        else:
            self.click(actual_target, offset=offset)

        time.sleep(wait_time)

    # ==================== Swipe / Slide / Fling ====================

    def swipe(self, direction: str, distance: int = 60, area=None,
              side: str = None, start_point: tuple = None,
              swipe_time: float = 0.3, speed: int = None):
        """
        在屏幕上或指定区域执行滑动操作。

        @param direction: "LEFT" / "RIGHT" / "UP" / "DOWN"
        @param distance: 滑动距离百分比 1-100，默认60
        @param area: 滑动区域控件 (BY selector / ArkUIXComponent / dict)
        @param side: 滑动位置 "LEFT"/"RIGHT"/"TOP"/"BOTTOM"
        @param start_point: 起始点坐标 (x, y)，支持比例坐标
        @param swipe_time: 滑动时间(秒)，默认0.3s
        @param speed: 滑动速度(像素/秒)，指定后 swipe_time 不生效
        """
        if direction.upper() not in DIRECTION_MAP:
            raise ValueError(f"invalid direction: {direction}")
        if distance < 1 or distance > 100:
            raise ValueError(f"distance [{distance}] out of range [1, 100]")

        start, end = self._generate_swipe_position(direction, distance, side, start_point, area)
        start_x, start_y = int(start[0]), int(start[1])
        end_x, end_y = int(end[0]), int(end[1])

        cmd_speed = 0
        if speed is not None:
            if speed < 200 or speed > 40000:
                raise ValueError(f"speed must be in [200, 40000], got {speed}")
            cmd_speed = speed
        elif swipe_time > 0:
            dist_px = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
            cmd_speed = int(dist_px / swipe_time)
            cmd_speed = max(200, min(40000, cmd_speed))

        self._client.send_command(SocketCommand.DRIVER_SWIPE, {
            "startX": start_x, "startY": start_y,
            "endX": end_x, "endY": end_y,
            "speed": cmd_speed,
        })

    def slide(self, start, end, area=None, slide_time: float = 1.0):
        """
        从起点滑到终点的精确滑动操作。
        @param start: 起点 (x, y) 或 BY 选择器
        @param end: 终点 (x, y) 或 BY 选择器
        @param area: 区域控件
        @param slide_time: 滑动时间(秒)
        """
        start_x, start_y = self._resolve_position(start, area)
        end_x, end_y = self._resolve_position(end, area)

        dist_px = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
        cmd_speed = int(dist_px / slide_time) if slide_time > 0 and dist_px > 0 else 600

        logger.debug(
            "slide: start=(%s,%s) end=(%s,%s) speed=%s",
            int(start_x), int(start_y), int(end_x), int(end_y), cmd_speed
        )
        self._client.send_command(SocketCommand.DRIVER_SWIPE, {
            "startX": int(start_x), "startY": int(start_y),
            "endX": int(end_x), "endY": int(end_y),
            "speed": cmd_speed,
        })

    def drag(self, start, end, area=None, press_time: float = 1.5,
             drag_time: float = 1.0, speed: int = None):
        """
        拖拽操作。使用服务端 DRIVER_DRAG 命令实现。
        @param start: 起点 (x, y) 或 BY 选择器
        @param end: 终点 (x, y) 或 BY 选择器
        @param area: 区域控件
        @param press_time: 长按时间(秒)
        @param drag_time: 拖拽移动时间(秒)
        @param speed: 拖拽速度(像素/秒)
        """
        start_x, start_y = self._resolve_position(start, area)
        end_x, end_y = self._resolve_position(end, area)

        cmd_speed = 0
        if speed is not None:
            if speed < 200 or speed > 40000:
                raise ValueError("speed must in the range [200, 40000]")
            cmd_speed = speed
        elif drag_time > 0:
            dist_px = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
            cmd_speed = int(dist_px / drag_time)
            cmd_speed = max(200, min(40000, cmd_speed))

        self._client.send_command(SocketCommand.DRIVER_DRAG, {
            "startX": int(start_x), "startY": int(start_y),
            "endX": int(end_x), "endY": int(end_y),
            "speed": cmd_speed,
        })

    def fling(self, direction: str, speed: str = "fast"):
        """
        快速滑动（惯性滑动）操作。
        @param direction: "LEFT" / "RIGHT" / "UP" / "DOWN"
        @param speed: 速度 "normal" / "fast" / "slow" or int
        """
        direction_int = DIRECTION_MAP.get(direction.upper())
        if direction_int is None:
            raise ValueError(f"invalid direction: {direction}")

        fling_speed = 0
        if speed == "fast":
            fling_speed = 40000
        elif speed == "slow":
            fling_speed = 200
        elif speed == "normal":
            fling_speed = 20000
        else:
            raise ValueError(f"invalid speed: {speed!r}")

        self._client.send_command(SocketCommand.DRIVER_FLING_DIRECTION, {
            "direction": direction_int,
            "speed": fling_speed,
        })

    # ==================== Component finding ====================

    def find_component(self, target, scroll_target=None) -> Optional[ArkUIXComponent]:
        """
        根据条件查找控件，返回第一个匹配的控件对象。
        @param target: BY 选择器 / dict / ArkUIXComponent
        @param scroll_target: 在指定可滚动控件中搜索
        @return: ArkUIXComponent 或 None
        """
        if isinstance(target, ArkUIXComponent):
            return target
        if not self._is_selector_target(target):
            return None

        on_dict = _on_dict_from_selector(target)

        if scroll_target is not None:
            scroll_comp = self.find_component(scroll_target)
            if scroll_comp is None:
                return None
            return scroll_comp.scroll_search(on_dict)

        result = self._client.send_command(SocketCommand.DRIVER_FIND_COMPONENT, {"on": on_dict})
        return self._wrap_component(result)

    def find_all_components(self, target, index: int = None):
        """
        根据条件查找所有匹配的控件。
        @param target: BY 选择器 / dict
        @param index: 返回第 index 个控件，None 则返回列表
        @return: ArkUIXComponent / List[ArkUIXComponent] / None
        """
        if not self._is_selector_target(target):
            return []

        on_dict = _on_dict_from_selector(target)
        result = self._client.send_command(SocketCommand.DRIVER_FIND_COMPONENTS, {"on": on_dict})

        if result is None:
            return []

        # Server returns a JSON array of ComponentInfo objects
        components = []
        if isinstance(result, list):
            for item in result:
                comp = self._wrap_component(item)
                if comp:
                    components.append(comp)

        if not components:
            return []
        if index is not None:
            if index >= len(components):
                logger.warning(f"Only {len(components)} components found, index {index} out of range")
                return None
            return components[index]
        return components

    # ==================== Key operations ====================

    def press_back(self):
        """按返回键"""
        self._client.send_command(SocketCommand.DRIVER_PRESS_BACK)

    @staticmethod
    def _to_key_int(key) -> int:
        """Convert KeyCode enum or int to int value."""
        if hasattr(key, 'value'):
            return key.value
        return int(key)

    def press_key(self, key_code, key_code2=None):
        """
        按键操作。
        @param key_code: 按键码 (int 或 KeyCode 枚举)
        @param key_code2: 第二个按键码（组合键）
        """
        key_code = self._to_key_int(key_code)
        if key_code2 is not None:
            key_code2 = self._to_key_int(key_code2)
            params = {"key0": key_code, "key1": key_code2}
            self._client.send_command(SocketCommand.DRIVER_TRIGGER_COMBINE_KEYS, params)
        else:
            self._client.send_command(SocketCommand.DRIVER_TRIGGER_KEY, {"keyCode": key_code})

    def press_combination_key(self, key1, key2, key3=None):
        """组合键操作"""
        params = {"key0": self._to_key_int(key1), "key1": self._to_key_int(key2)}
        if key3 is not None:
            params["key2"] = self._to_key_int(key3)
        self._client.send_command(SocketCommand.DRIVER_TRIGGER_COMBINE_KEYS, params)

    def go_back(self):
        """返回上一页"""
        self.press_back()

    # ==================== Display ====================

    def get_display_size(self) -> Tuple[int, int]:
        """
        获取屏幕分辨率（物理像素）。
        @return: (width, height) 物理像素
        """
        if self._display_size:
            return self._display_size
        params = {"displayId": 0}
        try:
            result = self._client.send_command(SocketCommand.DRIVER_GET_DISPLAY_SIZE, params)
            if isinstance(result, dict) and "x" in result and "y" in result:
                w, h = int(result["x"]), int(result["y"])
                self._display_size = (w, h)
                logger.info(f"get_display_size from C++: {w}x{h}, display_id=0")
                return (w, h)
        except Exception as e:
            logger.warning(f"get_display_size from C++ failed: {e}")
        # 回退到平台工具
        if self._platform == self.PLATFORM_ANDROID:
            try:
                import subprocess
                cmd = ["adb", "shell", "wm", "size"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                for line in result.stdout.strip().split('\n'):
                    if 'size' in line.lower():
                        parts = line.split(':')[-1].strip().split('x')
                        w, h = int(parts[0]), int(parts[1])
                        self._display_size = (w, h)
                        return (w, h)
            except Exception as e:
                logger.warning(f"Failed to get Android display size: {e}")

        message = f"get_display_size failed on ArkUI-X {self._platform}: unable to determine display size"
        logger.error(message)
        raise HypiumOperationFailError(message)

    def set_display_rotation(self, rotation: DisplayRotation):
        """设置屏幕旋转方向。"""
        rotation_value = rotation.value if hasattr(rotation, "value") else int(rotation)
        if rotation_value < DisplayRotation.ROTATION_0.value or rotation_value > DisplayRotation.ROTATION_270.value:
            raise ValueError(f"invalid rotation: {rotation}")
        self._client.send_command(SocketCommand.DRIVER_SET_DISPLAY_ROTATION, {
            "rotation": rotation_value,
        })

    # ==================== Timing ====================

    def wait(self, wait_time: float):
        """等待指定秒数"""
        time.sleep(wait_time)

    # ==================== Component property shortcuts ====================

    def get_component_property(self, component, property_name: str) -> Any:
        """
        获取控件属性值。
        @param component: BY 选择器 / ArkUIXComponent
        @param property_name: "id" / "text" / "type" / "enabled" / "bounds" 等
        """
        logger.debug("get_component_property: component=%r, property=%s", component, property_name)
        if isinstance(component, ArkUIXComponent):
            comp = component
            logger.debug("using existing ArkUIXComponent: id=%s, cached_text=%r", comp.component_id, comp.text)
        else:
            if not self._is_selector_target(component):
                self._raise_invalid_ui_target(component)
            comp = self.find_component(component)
            if comp is None:
                self._raise_component_not_found()
            logger.debug("find_component returned: id=%s", comp.component_id)

        property_map = {
            "id": comp.get_id,
            "text": comp.get_text,
            "type": comp.get_type,
            "bounds": comp.get_bounds,
            "enabled": comp.is_enabled,
            "focused": comp.is_focused,
            "clickable": comp.is_clickable,
            "scrollable": comp.is_scrollable,
            "checked": comp.is_checked,
            "checkable": comp.is_checkable,
            "selected": comp.is_selected,
        }
        getter = property_map.get(property_name)
        if getter is None:
            raise ValueError(f"invalid property: {property_name}")
        result = getter()
        logger.debug("%s getter returned: %r", property_name, result)
        return result

    def get_component_pos(self, component):
        """获取控件中心点坐标"""
        if isinstance(component, ArkUIXComponent):
            comp = component
        else:
            if not self._is_selector_target(component):
                self._raise_invalid_ui_target(component)
            comp = self.find_component(component)
        if comp is None:
            self._raise_component_not_found()
        result = comp._send(SocketCommand.COMPONENT_GET_BOUNDS_CENTER)
        if isinstance(result, dict):
            return (int(result.get("x", 0)), int(result.get("y", 0)))

        bounds = self.get_component_property(comp, "bounds")
        if bounds is None:
            return None
        return ((bounds.left + bounds.right) // 2, (bounds.top + bounds.bottom) // 2)

    # ==================== Input ====================

    def input_text(self, component, text: str, mode: None):
        """
        向控件输入文本。
        @param component: BY 选择器 / ArkUIXComponent
        @param text: 文本内容
        """
        if isinstance(component, tuple):
            raise RuntimeError("invalid point to click")
        if isinstance(component, ArkUIXComponent):
            comp = component
        else:
            if not self._is_selector_target(component):
                self._raise_invalid_ui_target(component)
            comp = self.find_component(component)
        if comp is None:
            self._raise_component_not_found()
        comp.click()  # Focus first
        time.sleep(0.3)
        comp.input_text(text)

    # ==================== Pinch ====================

    def _gen_pinch_in(self, area, scale, direction="diagonal", dead_zone_ratio=0.2, path_vibrate=False):
        if scale < 0 or scale > 1:
            raise RuntimeError(f"valid range is [0, 1], get {scale}")
        if dead_zone_ratio < 0 or dead_zone_ratio > 0.5:
            raise RuntimeError(f"valid range is [0, 0.5], get {dead_zone_ratio}")
        scale = (1 - scale) * 0.5
        if isinstance(area, Rect):
            bounds = area
        else:
            component = area if isinstance(area, ArkUIXComponent) else self.find_component(area)
            if (component is None):
                raise RuntimeError(f"Component not found: {area}")
            bounds = component.getBounds()
        width, height = bounds.get_size()
        if direction == "diagonal":
            start_x1 = bounds.left + int(dead_zone_ratio * width)
            start_y1 = bounds.top + int(dead_zone_ratio * height)
            start_x2 = bounds.right - int(dead_zone_ratio * width)
            start_y2 = bounds.bottom - int(dead_zone_ratio * height)
            end_x1 = start_x1 + int(width * 0.5 * scale)
            end_y1 = start_y1 + int(height * 0.5 * scale)
            end_x2 = start_x2 - int(width * 0.5 * scale)
            end_y2 = start_y2 - int(height * 0.5 * scale)
        elif direction == "horizontal":
            start_x1 = bounds.left + int(dead_zone_ratio * width)
            start_y1 = bounds.top + int(0.5 * height)
            start_x2 = bounds.right - int(dead_zone_ratio * width)
            start_y2 = bounds.bottom - int(0.5 * height)
            end_x1 = start_x1 + int(width * 0.5 * scale)
            end_y1 = start_y1
            end_x2 = start_x2 - int(width * 0.5 * scale)
            end_y2 = start_y2
        else:
            raise RuntimeError(msg="Invalid direction")

        params = [start_x1, start_y1, start_x2, start_y2, end_x1, end_y1, end_x2, end_y2]
        min_value = min(width, height)
        if scale > 0.1 and dead_zone_ratio > 0.05 and path_vibrate:
            for i in range(len(params)):
                params[i] += random.randint(-int(min_value * 0.05), int(min_value * 0.05))
        return params

    def pinch_in(self, area, scale: float = 0.4, direction: str = "diagonal", **kwargs):
        """缩小手势"""
        if scale > 1:
            raise RuntimeError("scale should be in range 0~1")
        if area is None:
            w, h = self.get_display_size()
            area = Rect(right=w, bottom=h)
        params = self._gen_pinch_in(area, scale, direction, **kwargs)
        start_x1, start_y1, start_x2, start_y2, end_x1, end_y1, end_x2, end_y2 = params
        self.two_finger_swipe((start_x1, start_y1), (end_x1, end_y1), (start_x2, start_y2), (end_x2, end_y2))

    @staticmethod
    def _calculate_two_finger_swipe_steps(distance: float, duration_s: float,
                                          sampling_time_ms: int = 50,
                                          min_steps: int = 2,
                                          max_steps: int = 12) -> int:
        """根据距离和时长估算 two_finger_swipe 需要的注入步数。"""
        if distance < 1 or duration_s <= 0:
            return min_steps

        time_ms = int(duration_s * 1000)
        if time_ms < sampling_time_ms:
            return min_steps

        steps = int(time_ms / sampling_time_ms)
        if steps > int(distance):
            steps = int(distance)
        if steps < min_steps:
            return min_steps
        if steps > max_steps:
            return max_steps
        return steps

    # ==================== Two-finger swipe ====================

    def two_finger_swipe(self, start1: tuple, end1: tuple,
                         start2: tuple, end2: tuple,
                         duration: float = 0.5, area=None):
        """
        双指滑动操作，通过 DRIVER_INJECT_MULTI_POINTER_ACTION 实现。
        @param start1: 第一根手指起点 (x, y)
        @param end1: 第一根手指终点 (x, y)
        @param start2: 第二根手指起点 (x, y)
        @param end2: 第二根手指终点 (x, y)
        @param duration: 滑动时长(秒)
        @param area: 忽略（兼容接口）
        """
        if not isinstance(duration, (int, float)):
            raise TypeError("unsupported operand type")

        dist1 = math.sqrt((end1[0] - start1[0]) ** 2 + (end1[1] - start1[1]) ** 2)
        dist2 = math.sqrt((end2[0] - start2[0]) ** 2 + (end2[1] - start2[1]) ** 2)
        max_dist = max(dist1, dist2)
        steps = self._calculate_two_finger_swipe_steps(max_dist, float(duration))

        points = []
        for s in range(steps):
            t = s / (steps - 1) if steps > 1 else 0
            x0 = int(start1[0] + (end1[0] - start1[0]) * t)
            y0 = int(start1[1] + (end1[1] - start1[1]) * t)
            points.append({"finger": 0, "step": s, "x": x0, "y": y0})
            x1 = int(start2[0] + (end2[0] - start2[0]) * t)
            y1 = int(start2[1] + (end2[1] - start2[1]) * t)
            points.append({"finger": 1, "step": s, "x": x1, "y": y1})

        speed = int(max_dist / duration)
        speed = max(200, min(40000, speed))

        self._client.send_command(SocketCommand.DRIVER_INJECT_MULTI_POINTER_ACTION, {
            "fingers": 2,
            "steps": steps,
            "points": points,
            "speed": speed,
        })

    # ==================== Shell-backed helpers ====================

    def _raise_unsupported(self, api_name: str, reason: str):
        message = f"{api_name}: unsupported on ArkUI-X {self._platform}. {reason}"
        logger.warning(message)
        raise HypiumNotSupportError(self._platform, message)

    def _raise_operation_failed(self, api_name: str, reason: str):
        message = f"{api_name} failed on ArkUI-X {self._platform}. {reason}"
        logger.warning(message)
        raise HypiumOperationFailError(message)

    @staticmethod
    def _command_output(result: subprocess.CompletedProcess) -> str:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if stdout and stderr:
            return f"{stdout}\n{stderr}"
        return stdout or stderr

    @staticmethod
    def _format_command_error(cmd: List[str], result: subprocess.CompletedProcess) -> str:
        detail = ArkUIXDriver._command_output(result) or f"exit code {result.returncode}"
        return f"{' '.join(cmd)} failed: {detail}"

    def _run_command(self, cmd: List[str], timeout: float = 60, check: bool = False) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"command not found: {cmd[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{' '.join(cmd)} timed out after {timeout}s") from exc
        except Exception as exc:
            raise RuntimeError(f"{' '.join(cmd)} failed: {exc}") from exc

        if check and result.returncode != 0:
            raise RuntimeError(self._format_command_error(cmd, result))
        return result

    def _build_adb_cmd(self, *args: str) -> List[str]:
        cmd = ["adb"]
        if self._device_id:
            cmd.extend(["-s", self._device_id])
        cmd.extend(args)
        return cmd

    def _run_adb_command(self, args: List[str], timeout: float = 60, check: bool = False) -> subprocess.CompletedProcess:
        if shutil.which("adb") is None:
            raise RuntimeError("adb not found")
        return self._run_command(self._build_adb_cmd(*args), timeout=timeout, check=check)

    def _run_adb_shell(self, cmd: str, timeout: float = 60, check: bool = False) -> subprocess.CompletedProcess:
        return self._run_adb_command(["shell", "sh", "-c", cmd], timeout=timeout, check=check)

    def _run_android_shell_command(self, cmd: str, timeout: float = 60,
                                   check: bool = False) -> subprocess.CompletedProcess:
        if cmd is None or not isinstance(cmd, str):
            raise RuntimeError("expected string or bytes-like object")
        if not cmd or not cmd.strip():
            raise RuntimeError("shell command is empty")

        stripped = cmd.strip()
        needs_shell = bool(re.search(r"[|&;<>()$`\n]", stripped))
        if needs_shell:
            return self._run_adb_shell(stripped, timeout=timeout, check=check)

        try:
            parts = shlex.split(stripped, posix=True)
        except ValueError:
            return self._run_adb_shell(stripped, timeout=timeout, check=check)

        if not parts:
            raise RuntimeError("shell command is empty")
        return self._run_adb_command(["shell", *parts], timeout=timeout, check=check)

    def _require_ios_device_id(self, api_name: str):
        if not self._device_id:
            raise RuntimeError(f"{api_name} requires iOS device_id for xcrun devicectl")

    @staticmethod
    def _extract_devicectl_error(data: dict) -> str:
        error = data.get("error", {})
        description = error.get("userInfo", {}).get("NSLocalizedDescription", {})
        if isinstance(description, dict):
            message = description.get("string")
            if message:
                return message
        return error.get("description") or ""

    def _run_devicectl_json(self, args: List[str], timeout: float = 60) -> dict:
        self._require_ios_device_id("devicectl")
        if shutil.which("xcrun") is None:
            raise RuntimeError("xcrun not found")

        json_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="arkuix-devicectl-", suffix=".json", delete=False) as fp:
                json_path = fp.name
            result = self._run_command(
                ["xcrun", "devicectl", *args, "--json-output", json_path],
                timeout=timeout,
                check=False,
            )
            if not os.path.exists(json_path):
                raise RuntimeError("devicectl did not produce json output")
            with open(json_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        finally:
            if json_path and os.path.exists(json_path):
                os.remove(json_path)

        outcome = data.get("info", {}).get("outcome")
        if result.returncode != 0 or outcome == "failed":
            detail = self._extract_devicectl_error(data) or self._command_output(result) or "unknown error"
            raise RuntimeError(f"devicectl {' '.join(args)} failed: {detail}")
        return data

    @staticmethod
    def _file_url_to_path(file_url: str) -> str:
        if not file_url:
            return ""
        parsed = urlparse(file_url)
        if parsed.scheme == "file":
            return parsed.path
        return file_url

    # ==================== Shell-backed platform APIs ====================

    def _ios_get_device_details(self) -> dict:
        return self._run_devicectl_json(
            ["device", "info", "details", "--device", self._device_id],
            timeout=15,
        ).get("result", {})

    def _ios_get_apps(self, bundle_id: str = None) -> List[dict]:
        args = ["device", "info", "apps", "--device", self._device_id]
        if bundle_id:
            args.extend(["--bundle-id", bundle_id])
        result = self._run_devicectl_json(args, timeout=20).get("result", {})
        return result.get("apps") or []

    def _ios_get_running_processes(self) -> List[dict]:
        result = self._run_devicectl_json(
            ["device", "info", "processes", "--device", self._device_id],
            timeout=20,
        ).get("result", {})
        return result.get("runningProcesses") or []

    def _ios_find_process_pid(self, package_name: str) -> Optional[int]:
        apps = self._ios_get_apps(package_name)
        if not apps:
            return None

        app_path = self._file_url_to_path(apps[0].get("url", "")).rstrip("/")
        app_name = os.path.basename(app_path)
        for process in self._ios_get_running_processes():
            executable = self._file_url_to_path(process.get("executable", ""))
            if not executable:
                continue
            if app_path and executable.startswith(app_path + "/"):
                return process.get("processIdentifier")
            if app_name and f"/{app_name}/" in executable:
                return process.get("processIdentifier")
        return None

    def _android_resolve_launch_component(self, package_name: str) -> Optional[str]:
        resolve_cmds = [
            ["shell", "cmd", "package", "resolve-activity", "--brief", package_name],
            ["shell", "cmd", "package", "resolve-activity", "--brief", "-c", "android.intent.category.LAUNCHER", package_name],
            # ["shell", "dumpsys", "package", package_name],
        ]
        component_pattern = re.compile(rf"({re.escape(package_name)}/[A-Za-z0-9._$]+)")

        for cmd in resolve_cmds:
            try:
                result = self._run_adb_command(cmd, timeout=20, check=False)
            except RuntimeError as exc:
                logger.warning(f"resolve launch component failed for [{' '.join(cmd[1:])}]: {exc}")
                continue
            text = self._command_output(result)
            for line in reversed(text.splitlines()):
                match = component_pattern.search(line.strip())
                if match:
                    return match.group(1)
        return None

    def _android_is_display_on(self) -> Optional[bool]:
        dumpsys_outputs = []
        dumpsys_commands = [
            ["shell", "dumpsys", "display"],
            ["shell", "dumpsys", "power"],
        ]

        for cmd in dumpsys_commands:
            try:
                dumpsys_outputs.append(
                    self._command_output(self._run_adb_command(cmd, timeout=15, check=False))
                )
            except RuntimeError as exc:
                logger.warning(f"android display state probe failed for [{' '.join(self._build_adb_cmd(*cmd))}]: {exc}")
                continue

        for text in dumpsys_outputs:
            if not text:
                continue
            for pattern in (r"mScreenState=(\w+)", r"Display Power: state=(\w+)", r"state=(ON|OFF|DOZE|DOZE_SUSPEND)"):
                match = re.search(pattern, text)
                if match:
                    state = match.group(1).upper()
                    if state == "OFF":
                        return False
                    if state in ("ON", "DOZE", "DOZE_SUSPEND", "VR"):
                        return True
        return None

    def _android_input_keyevent(self, key_name: str):
        self._run_adb_command(["shell", "input", "keyevent", key_name], timeout=10, check=True)

    def _android_is_locked(self) -> bool:
        dumpsys_commands = [
            ["shell", "dumpsys", "window"],
            ["shell", "dumpsys", "trust"],
        ]
        outputs = []

        for cmd in dumpsys_commands:
            try:
                outputs.append(self._command_output(self._run_adb_command(cmd, timeout=15, check=False)))
            except RuntimeError as exc:
                logger.warning(f"android lock-state probe failed for [{' '.join(self._build_adb_cmd(*cmd))}]: {exc}")

        false_patterns = (
            r"mDreamingLockscreen\s*=\s*false",
            r"isStatusBarKeyguard\s*=\s*false",
            r"showing\s*=\s*false",
            r"screenLocked\s*=\s*false",
            r"deviceLocked\s*=\s*false",
        )
        true_patterns = (
            r"mDreamingLockscreen\s*=\s*true",
            r"isStatusBarKeyguard\s*=\s*true",
            r"showing\s*=\s*true",
            r"screenLocked\s*=\s*true",
            r"deviceLocked\s*=\s*true",
        )

        for text in outputs:
            if not text:
                continue
            for pattern in false_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return False
            for pattern in true_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True

        logger.warning("is_locked: unable to determine lock state from dumpsys output, fallback to False")
        return False

    def get_device_type(self) -> str:
        if self._platform == self.PLATFORM_IOS:
            try:
                details = self._ios_get_device_details()
            except RuntimeError as exc:
                raise HypiumOperationFailError(
                    f"get_device_type failed on ArkUI-X {self._platform}. {exc}"
                ) from exc
            hardware = details.get("hardwareProperties", {})
            device_type = str(hardware.get("deviceType") or "").lower()
            product_type = str(hardware.get("productType") or "").lower()
            marketing_name = str(hardware.get("marketingName") or "").lower()
            families = set(hardware.get("supportedDeviceFamilies") or [])

            if 2 in families or "ipad" in device_type or "ipad" in product_type or "ipad" in marketing_name:
                return "tablet"
            if 1 in families or "iphone" in device_type or "iphone" in product_type or "iphone" in marketing_name:
                return "phone"
            if 4 in families or "watch" in device_type or "watch" in product_type or "watch" in marketing_name:
                return "wearable"

            self._raise_operation_failed("get_device_type", f"unrecognized iOS hardware info: {hardware}")

        if self._platform == self.PLATFORM_ANDROID:
            try:
                result = self._run_adb_command(["shell", "getprop", "ro.build.characteristics"], timeout=10, check=False)
            except RuntimeError as exc:
                raise HypiumOperationFailError(
                    f"get_device_type failed on ArkUI-X {self._platform}. {exc}"
                ) from exc

            output = self._command_output(result).strip().lower()
            if not output:
                raise HypiumOperationFailError(
                    f"get_device_type failed on ArkUI-X {self._platform}. empty ro.build.characteristics"
                )

            tokens = [token.strip() for token in output.split(",") if token.strip()]
            normalized = {
                "watch": "wearable",
                "wearable": "wearable",
                "phone": "phone",
                "tablet": "tablet",
                "default": "default",
                "sdcard": "sdcard",
                "nosdcard": "nosdcard",
            }

            for preferred in ("phone", "tablet", "wearable", "sdcard", "nosdcard", "default"):
                for token in tokens:
                    mapped = normalized.get(token)
                    if mapped == preferred:
                        return mapped

            mapped_output = normalized.get(output)
            if mapped_output:
                return mapped_output

            raise HypiumOperationFailError(
                f"get_device_type failed on ArkUI-X {self._platform}. unsupported ro.build.characteristics: {output}"
            )

        self._raise_unsupported("get_device_type", f"unknown platform {self._platform}")

    @property
    def log(self):
        return logger

    def shell(self, cmd: str, timeout: float = 60) -> str:
        if self._platform == self.PLATFORM_ANDROID:
            try:
                result = self._run_android_shell_command(cmd, timeout=timeout, check=False)
                return self._command_output(result)
            except RuntimeError as exc:
                raise HypiumOperationFailError(
                    f"shell failed on ArkUI-X {self._platform}. {exc}"
                ) from exc

        self._raise_unsupported("shell", "iOS real devices do not expose a stable shell via devicectl")

    def get_language(self) -> str:
        if self._platform == self.PLATFORM_ANDROID:
            result = self._run_adb_command(["shell", "getprop", "persist.sys.locale"], timeout=30, check=False)
            output = self._command_output(result)
            if result.returncode != 0:
                raise HypiumOperationFailError("Fail to get language")
            return output

        self._raise_unsupported("get_language", "iOS real devices do not expose app data clear via devicectl")

    # ==================== Shell-backed app / device management ====================

    def _is_socket_alive(self) -> bool:
        """通过发送轻量命令检测应用是否仍在运行。"""
        if not self._client.is_connected:
            return False
        try:
            self._client.send_command(SocketCommand.DRIVER_DELAY_MS, {"duration": 0})
            return True
        except Exception:
            return False

    def _launch_app_directly(self, package_name: str, page_name: str = None, params: str = "") -> bool:
        """使用平台原生命令直接拉起应用。"""
        if self._platform == self.PLATFORM_IOS:
            self._require_ios_device_id("start_app")
            if page_name:
                logger.warning("start_app: iOS devicectl does not support page_name; ignoring it")
            cmd = [
                "xcrun", "devicectl", "device", "process", "launch",
                "--device", self._device_id,
                "--activate",
                package_name,
            ]
            if params:
                cmd.extend(shlex.split(params))
        elif self._platform == self.PLATFORM_ANDROID:
            if page_name:
                component = page_name if "/" in page_name else f"{package_name}/{page_name}"
            else:
                component = self._android_resolve_launch_component(package_name)

            if component:
                cmd = self._build_adb_cmd("shell", "am", "start", "-n", component, "--activity-clear-top", "--activity-single-top")
                if params:
                    cmd.extend(shlex.split(params))
            else:
                if page_name or params:
                    logger.warning("start_app: launch activity unresolved, fallback monkey ignores page_name/params")
                cmd = self._build_adb_cmd(
                    "shell", "monkey",
                    "-p", package_name,
                    "-c", "android.intent.category.LAUNCHER",
                    "1",
                )
        else:
            self._raise_unsupported("start_app", f"unknown platform {self._platform}")

        logger.info(f"[ArkUIX] launch_app: command = {' '.join(cmd)}")
        try:
            result = self._run_command(cmd, timeout=20, check=False)
        except RuntimeError as exc:
            logger.warning(f"[ArkUIX] launch_app failed: {exc}")
            return False

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            logger.info(f"[ArkUIX] launch_app stdout: {stdout}")
        if stderr:
            logger.info(f"[ArkUIX] launch_app stderr: {stderr}")
        return result.returncode == 0

    def _retry_connect_until_socket_connected(self, timeout: float = 30.0, retry_interval: float = 2.0) -> bool:
        """循环重试连接，直到 socket 通道可用。"""
        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            attempt += 1
            try:
                self._client.connect(retry_times=1, retry_interval=0.5)
            except Exception:
                elapsed = int(time.time() - start_time)
                logger.info(f"[ArkUIX] start_app: TCP connect failed ({elapsed}s elapsed), retrying...")
                time.sleep(retry_interval)
                continue

            if self._is_socket_alive():
                elapsed = int(time.time() - start_time)
                logger.info(f"[ArkUIX] start_app: app is ready! ({elapsed}s elapsed, attempt {attempt})")
                return True

            self._client.disconnect()
            elapsed = int(time.time() - start_time)
            logger.info(f"[ArkUIX] start_app: app not ready ({elapsed}s elapsed), retrying...")
            time.sleep(retry_interval)

        return False

    def start_app(self, package_name: str, page_name: str = None, params: str = "",
                  wait_time: float = 1, **kwargs):
        """
        启动 ArkUI-X 应用。
        - Android: adb shell am start / monkey
        - iOS 真机: xcrun devicectl device process launch

        @param package_name: 应用包名，如 "com.example.arkuitest"
        @param page_name: 兼容参数，当前未使用
        """
        if not package_name:
            raise HypiumOperationFailError("start_app failed: package_name is empty")

        if not self._launch_app_directly(package_name, page_name=page_name, params=params):
            raise HypiumOperationFailError("start_app failed: launch command execution failed")

        if wait_time > 0:
            time.sleep(wait_time)

        # 启动后如果当前连接已可用，直接返回；否则走重连等待。
        if self._is_socket_alive():
            logger.info("[ArkUIX] start_app: socket is alive after launch command")
            return

        logger.info("[ArkUIX] start_app: waiting for socket to be ready...")
        self._client.disconnect()
        if not self._retry_connect_until_socket_connected():
            raise HypiumOperationFailError("start_app failed: socket did not become ready within timeout")

    def stop_app(self, package_name: str, wait_time: float = 0.5, **kwargs):
        if self._platform == self.PLATFORM_ANDROID:
            self._run_adb_command(["shell", "am", "force-stop", package_name], timeout=15, check=True)
        elif self._platform == self.PLATFORM_IOS:
            pid = self._ios_find_process_pid(package_name)
            if pid is None:
                logger.info(f"stop_app: iOS app is not running. package={package_name}")
            else:
                self._run_command(
                    [
                        "xcrun", "devicectl", "device", "process", "terminate",
                        "--device", self._device_id,
                        "--pid", str(pid),
                    ],
                    timeout=20,
                    check=True,
                )
        else:
            self._raise_unsupported("stop_app", f"unknown platform {self._platform}")

        if wait_time > 0:
            time.sleep(wait_time)
        logger.info(f"stop_app: disconnecting socket. package={package_name}")
        self._client.disconnect()

    def has_app(self, package_name: str) -> bool:
        try:
            if self._platform == self.PLATFORM_ANDROID:
                result = self._run_adb_command(["shell", "pm", "path", package_name], timeout=10, check=False)
                return "package:" in (result.stdout or "")
            if self._platform == self.PLATFORM_IOS:
                return bool(self._ios_get_apps(package_name))
        except RuntimeError as exc:
            logger.warning(f"has_app failed for {package_name}: {exc}")
        return False

    def uninstall_app(self, package_name: str, **kwargs):
        if self._platform == self.PLATFORM_ANDROID:
            self._run_adb_command(["uninstall", package_name], timeout=60, check=True)
        elif self._platform == self.PLATFORM_IOS:
            if not self.has_app(package_name):
                raise RuntimeError(f"uninstall_app failed: app not installed: {package_name}")
            self._run_devicectl_json(
                [
                    "device", "uninstall", "app",
                    "--device", self._device_id,
                    package_name,
                ],
                timeout=60,
            )
        else:
            self._raise_unsupported("uninstall_app", f"unknown platform {self._platform}")

        self._client.disconnect()

    def clear_app_data(self, package_name: str):
        if self._platform == self.PLATFORM_ANDROID:
            result = self._run_adb_command(["shell", "pm", "clear", package_name], timeout=30, check=False)
            output = self._command_output(result)
            if result.returncode != 0 or "Success" not in output:
                raise HypiumOperationFailError("Fail to clean cache")
            return

        self._raise_unsupported("clear_app_data", "iOS real devices do not expose app data clear via devicectl")

    def wake_up_display(self):
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("wake_up_display", "only Android has a stable adb keyevent flow")

        try:
            self._android_input_keyevent("WAKEUP")
            return
        except Exception as exc:
            logger.warning(f"wake_up_display: WAKEUP keyevent failed, fallback to POWER. {exc}")

        is_on = self._android_is_display_on()
        if is_on is False:
            self.press_power()
            return
        elif is_on is None:
            logger.warning("wake_up_display: unable to determine display state, skip power key toggle")

    def close_display(self):
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("close_display", "only Android has a stable adb keyevent flow")

        is_on = self._android_is_display_on()
        if is_on is True:
            self.press_power()
        elif is_on is None:
            logger.warning("close_display: unable to determine display state, skip power key toggle")

    def is_display_on(self) -> bool:
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("is_display_on", "only Android has a stable adb display-state flow")

        is_on = self._android_is_display_on()
        return bool(is_on)

    def is_display_locked(self) -> bool:
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("is_display_locked", "only Android has a stable adb lock-state flow")

        is_locked = self._android_is_locked()
        return bool(is_locked)

    def press_home(self):
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("press_home", "iOS real devices do not expose a stable home action via devicectl")
        self._android_input_keyevent("HOME")

    def go_home(self):
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("go_home", "iOS real devices do not expose a stable home action via devicectl")
        self.press_home()

    def press_power(self):
        if self._platform != self.PLATFORM_ANDROID:
            self._raise_unsupported("press_power", "iOS real devices do not expose a stable power key action via devicectl")
        self._android_input_keyevent("POWER")

    # ==================== Internal helpers ====================

    def _wrap_component(self, result) -> Optional[ArkUIXComponent]:
        """Convert server response (ComponentInfo JSON) to ArkUIXComponent.

        Server returns ComponentInfo:
        {"componentId":"xxx","text":"...","type":"...","left":0,"top":0,
         "width":100,"height":50,"clickable":true,...}
        Or null/empty when not found.
        """
        if result is None:
            return None
        if isinstance(result, dict):
            component_id = result.get("componentId")
            if component_id:
                return ArkUIXComponent(self._client, component_id, result)
        return None

    def _to_abs_pos(self, x, y) -> Tuple[int, int]:
        """Convert position, supporting proportional coords (0.0~1.0)."""
        if isinstance(x, float) and 0 <= x <= 1.0 and isinstance(y, float) and 0 <= y <= 1.0:
            w, h = self.get_display_size()
            return int(x * w), int(y * h)
        return int(x), int(y)

    def _resolve_position(self, target, area=None) -> Tuple[int, int]:
        """Resolve a target (tuple/selector/component) to absolute (x, y)."""
        if area is not None and not isinstance(area, (Rect, ArkUIXComponent)) and not self._is_selector_target(area):
            self._raise_invalid_ui_target(area)

        if isinstance(target, tuple):
            x, y = target
            if area is not None:
                # Relative coords within area (supports proportional 0.0~1.0)
                bounds = None
                if isinstance(area, Rect):
                    bounds = area
                else:
                    area_comp = self.find_component(area) if not isinstance(area, ArkUIXComponent) else area
                    if area_comp:
                        bounds = self.get_component_property(area_comp, "bounds")

                if bounds:
                    logger.debug(
                        "_resolve_position: area bounds=(%s,%s,%s,%s)",
                        bounds.left, bounds.top, bounds.right, bounds.bottom
                    )
                    area_w = bounds.right - bounds.left
                    area_h = bounds.bottom - bounds.top
                    if isinstance(x, float) and 0 <= x <= 1.0:
                        x = x * area_w
                    if isinstance(y, float) and 0 <= y <= 1.0:
                        y = y * area_h
                    result = (bounds.left + int(x), bounds.top + int(y))
                    logger.debug("_resolve_position: resolved=(%s,%s)", result[0], result[1])
                    return result
            return self._to_abs_pos(x, y)
        elif isinstance(target, ArkUIXComponent):
            return self.get_component_pos(target)
        else:
            if not self._is_selector_target(target):
                self._raise_invalid_ui_target(target)
            comp = self.find_component(target)
            if comp is None:
                self._raise_component_not_found()
            return self.get_component_pos(comp)

    def _generate_center_swipe_start_point(self, side: str, center, direction, distance):
        center_x, center_y = center
        step = int(distance / 2)
        # 转换中心点
        if side == "TOP":
            center_y = int(center_y * 0.3)
        elif side == "BOTTOM":
            center_y = int(center_y * 1.8)
        elif side == "LEFT":
            center_x = int(center_x * 0.3)
        elif side == "RIGHT":
            center_x = int(center_x * 1.8)

        # 计算起始点
        if direction == "LEFT":
            start_x = center_x + step
            start_y = center_y
        elif direction == "RIGHT":
            start_x = center_x - step
            start_y = center_y
        elif direction == "UP":
            start_x = center_x
            start_y = center_y + step
        elif direction == "DOWN":
            start_x = center_x
            start_y = center_y - step
        else:
            raise ValueError(f"Invalid direction: {direction}")
        return start_x, start_y

    def _generate_swipe_end_point(self, start_point, direction, distance):
        start_x, start_y = start_point
        if direction == "LEFT":
            end_x = start_x - distance
            end_y = start_y
        elif direction == "RIGHT":
            end_x = start_x + distance
            end_y = start_y
        elif direction == "UP":
            end_x = start_x
            end_y = start_y - distance
        elif direction == "DOWN":
            end_x = start_x
            end_y = start_y + distance
        else:
            raise ValueError(f"Invalid direction: {direction}")
        return end_x, end_y

    def _generate_absolute_distance(self, direction, distance_scale, area_width, area_height) -> int:
        if direction in ("LEFT", "RIGHT"):
            return int(area_width * distance_scale)
        elif direction in ("UP", "DOWN"):
            return int(area_height * distance_scale)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def _scale_to_position(self, pos, area_size=None):
        if area_size is None:
            area_size = self.driver.getDisplaySize().to_tuple()
        width, height = area_size
        x, y = pos
        if 0 <= x <= 1 or 0 <= y <= 1:
            x = int(x * width)
            y = int(y * height)
        return x, y

    def _generate_swipe_position(self, direction: str, distance: int, side: str,
                                  start_point: tuple, area):
        """
        Generate swipe start/end positions.
        Logic aligned with OHOSDriver._generate_swipe_position.
        """
        base_x, base_y = 0, 0
        if distance < 0 or distance > 100:
            raise ValueError(f"distance [{distance}] is invalid, should be in range(0, 100)")

        if area is None:
            # 未指定区域时滑动区域为整个屏幕
            len_x, len_y = self.get_display_size()
            center_x, center_y = len_x / 2, len_y / 2
        else:
            # 指定区域时滑动区域为控件所在的区域
            if isinstance(area, Rect):
                bounds = area
            elif isinstance(area, ArkUIXComponent):
                bounds = self.get_component_property(area, "bounds")
            elif self._is_selector_target(area):
                area_comp = self.find_component(area)
                if area_comp is None:
                    self._raise_component_not_found()
                bounds = self.get_component_property(area_comp, "bounds")
            else:
                self._raise_invalid_ui_target(area)

            len_x = bounds.right - bounds.left
            len_y = bounds.bottom - bounds.top
            center_x = int((bounds.right + bounds.left) / 2)
            center_y = int((bounds.top + bounds.bottom) / 2)
            base_x = bounds.left
            base_y = bounds.top

        distance = self._generate_absolute_distance(direction, distance / 100, len_x, len_y)
        if start_point is None:
            start_point = self._generate_center_swipe_start_point(side, (center_x, center_y), direction, distance)
        else:
            start_point = self._scale_to_position(start_point, (len_x, len_y))
            # add area offset if the start point is specified by user.
            start_point = (start_point[0] + base_x, start_point[1] + base_y)
        end_point = self._generate_swipe_end_point(start_point, direction, distance)
        x, y = start_point
        x1, y1 = end_point
        if x < 0 or y < 0 or x1 < 0 or y1 < 0:
            raise ValueError("Invalid param, start or end point is negative, start %s, end %s, " \
                             "please note that param [distance] is the percent of screen width/height)" %
                             (start_point, end_point))
        return (int(start_point[0]), int(start_point[1])), (int(end_point[0]), int(end_point[1]))

    # ==================== Context manager ====================

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __repr__(self):
        status = "connected" if self.is_connected else "disconnected"
        return f"ArkUIXDriver(platform={self._platform}, {self._host}:{self._port}, {status})"
