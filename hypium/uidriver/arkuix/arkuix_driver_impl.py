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
ArkUI-X driver implementation adapter.

Wraps ArkUIXDriver to match the interface expected by UiDriver._driver_impl,
so that existing test scripts using UiDriver(device) work transparently
with ArkUI-X iOS/Android devices.

Architecture:
    UiDriver(device)
        └── _driver_impl = ArkUIXDriverImpl(device)
                └── _arkuix_driver = ArkUIXDriver(host, port, platform)
                        └── ArkUIXSocketClient (TCP socket)
"""

import time
import logging

from hypium.model.basic_data_type import DisplayRotation

from hypium.uidriver.arkuix.arkuix_driver import ArkUIXDriver, _on_dict_from_selector, DEFAULT_PORT
from hypium.uidriver.arkuix.arkuix_component import SocketCommand

logger = logging.getLogger("hypium.arkuix")

class _DriverProxy:
    """
    Minimal proxy object that satisfies UiDriver.__init__'s
    `setattr(self._driver_impl.driver, ...)` call.
    """
    pass

class ArkUIXDriverImpl:
    def __init__(self, device, **kwargs):
        """
        Args:
            device: ArkUIXDevice instance with host, port, platform attributes
        """
        self._device_obj = device
        self.driver = _DriverProxy()
        self.driver._device = self._device_obj

        host = device.host
        port = getattr(device, 'port', DEFAULT_PORT)
        platform = getattr(device, 'platform', 'ios')
        extra = getattr(device, 'extra', {})

        connect_timeout = extra.get('connect_timeout', 10.0)
        recv_timeout = extra.get('recv_timeout', 60.0)
        device_id = extra.get('device_id')

        self._arkuix_driver = ArkUIXDriver(
            host, port, platform=platform,
            connect_timeout=connect_timeout,
            recv_timeout=recv_timeout,
            device_id=device_id,
        )

        try:
            self._arkuix_driver.connect()
        except Exception as e:
            logger.error(f"[ArkUIX] ArkUIXDriverImpl init: connect failed - {e}")
            self._arkuix_driver.close()
            raise

    # ==================== log ====================

    @property
    def log(self):
        return logger

    @property
    def device_sn(self):
        return self._device_obj.device_sn

    @property
    def _device(self):
        return self._device_obj

    # ==================== find_component (core API) ====================

    def find_component(self, target, scroll_target=None):
        on_dict = self._to_on_dict(target)
        if on_dict is None:
            return None
        if scroll_target is not None:
            scroll_on_dict = self._to_on_dict(scroll_target)
            if scroll_on_dict is None:
                return None
            scroll_comp = self._arkuix_driver.find_component(scroll_on_dict)
            if scroll_comp is None:
                return None
            return scroll_comp.scroll_search(on_dict)
        return self._arkuix_driver.find_component(on_dict)

    def find_all_components(self, target, index=None):
        on_dict = self._to_on_dict(target)
        if on_dict is None:
            return []
        return self._arkuix_driver.find_all_components(on_dict, index=index)

    # ==================== click / touch ====================

    def click(self, target, offset=None):
        self._arkuix_driver.click(target, offset=offset)

    def double_click(self, target, offset=None):
        self._arkuix_driver.double_click(target, offset=offset)

    def long_click(self, target, press_time=2.0, offset=None):
        self._arkuix_driver.long_click(target, press_time=press_time, offset=offset)

    def touch(self, target, mode="normal", scroll_target=None, wait_time=0.1, offset=None):
        self._arkuix_driver.touch(target, mode=mode, scroll_target=scroll_target,
                                  wait_time=wait_time, offset=offset)

    # ==================== swipe / slide / drag / fling ====================

    def swipe(self, direction="UP", distance=60, area=None, side=None,
              start_point=None, swipe_time=0.3, speed=None):
        self._arkuix_driver.swipe(direction, distance=distance, area=area,
                                  side=side, start_point=start_point,
                                  swipe_time=swipe_time, speed=speed)

    def slide(self, start, end, area=None, slide_time=1.0):
        self._arkuix_driver.slide(start, end, area=area, slide_time=slide_time)

    def drag(self, start, end, area=None, press_time=1.5, drag_time=1.0, speed=None):
        self._arkuix_driver.drag(start, end, area=area, press_time=press_time,
                                 drag_time=drag_time, speed=speed)

    def fling(self, direction, distance=50, area=None, speed="fast"):
        self._arkuix_driver.fling(direction, speed=speed)

    # ==================== key operations ====================

    def press_back(self):
        self._arkuix_driver.press_back()

    def go_back(self):
        self._arkuix_driver.press_back()

    def press_key(self, key_code, key_code2=None, mode="normal"):
        # UiDriver passes (key_code, key_code2, mode) — mode is ignored for ArkUI-X
        if mode is not None and mode not in ("normal", "long", "double"):
            raise RuntimeError("invalid touch")
        self._arkuix_driver.press_key(key_code, key_code2)

    def press_combination_key(self, key1, key2, key3=None):
        self._arkuix_driver.press_combination_key(key1, key2, key3)

    # ==================== display ====================


    def get_display_size(self):
        return self._arkuix_driver.get_display_size()

    def set_display_rotation(self, rotation: DisplayRotation):
        return self._arkuix_driver.set_display_rotation(rotation)

    # ==================== timing ====================

    def wait(self, wait_time: float):
        self._arkuix_driver.wait(wait_time)

    # ==================== input ====================

    def input_text(self, component, text, mode = None):
        self._arkuix_driver.input_text(component, text, mode)

    # ==================== shell-backed ====================

    def get_device_type(self) -> str:
        return self._arkuix_driver.get_device_type()

    def start_app(self, package_name: str, page_name: str = None, params: str = "", wait_time: float = 1, **kwargs):
        self._arkuix_driver.start_app(
            package_name,
            page_name,
            params=params,
            wait_time=wait_time,
            **kwargs,
        )

    def stop_app(self, package_name: str, wait_time: float = 0.5, **kwargs):
        self._arkuix_driver.stop_app(package_name, wait_time=wait_time, **kwargs)

    def has_app(self, package_name: str) -> bool:
        return self._arkuix_driver.has_app(package_name)

    def uninstall_app(self, package_name: str, **kwargs):
        self._arkuix_driver.uninstall_app(package_name, **kwargs)

    def clear_app_data(self, package_name: str):
        self._arkuix_driver.clear_app_data(package_name)

    # ==================== component property shortcuts ====================

    def get_component_property(self, component, property_name: str):
        return self._arkuix_driver.get_component_property(component, property_name)

    def get_component_pos(self, component):
        return self._arkuix_driver.get_component_pos(component)

    # ==================== pinch ====================

    def pinch_in(self, area, scale=0.4, direction="diagonal", **kwargs):
        self._arkuix_driver.pinch_in(area, scale, direction, **kwargs)

    # ==================== two-finger swipe ====================

    def two_finger_swipe(self, start1, end1, start2, end2, duration=0.5, area=None):
        self._arkuix_driver.two_finger_swipe(start1, end1, start2, end2,
                                             duration=duration, area=area)

    # ==================== gesture injection ====================

    def _gestures_to_pointer_action(self, gestures, speed=2000):
        """将 Gesture 对象列表转换为 DRIVER_INJECT_MULTI_POINTER_ACTION 参数并发送"""
        fingers = len(gestures)
        # 取最大步骤数，短的手势用最后一个坐标填充
        max_steps = max(len(g.steps) for g in gestures)

        points = []
        for finger_idx, gesture in enumerate(gestures):
            steps = gesture.steps
            for step_idx in range(max_steps):
                if step_idx < len(steps):
                    pos = steps[step_idx].pos
                else:
                    pos = steps[-1].pos  # 用最后一个坐标填充
                points.append({
                    "finger": finger_idx,
                    "step": step_idx,
                    "x": int(pos[0]),
                    "y": int(pos[1]),
                })

        self._arkuix_driver._client.send_command(
            SocketCommand.DRIVER_INJECT_MULTI_POINTER_ACTION, {
                "fingers": fingers,
                "steps": max_steps,
                "points": points,
                "speed": speed,
            })

    def inject_multi_finger_gesture(self, gestures, speed=2000):
        """注入多指手势，兼容 OHOSDriver.inject_multi_finger_gesture"""
        if not gestures:
            raise ValueError("empty sequence")
        if not (200 <= speed <= 40000):
            raise ValueError("speed 必须在 200~40000 之间")
        for gesture in gestures:
            if not hasattr(gesture, "steps") and not hasattr(gesture, "area"):
                raise AttributeError(f"'{type(gesture).__name__}' object has no attribute 'area'")
        self._gestures_to_pointer_action(gestures, speed=speed)

    def inject_gesture(self, gesture, speed=2000):
        """注入单指手势，兼容 OHOSDriver.inject_gesture"""
        if not isinstance(speed, int):
            raise TypeError("Check arg1 failed")
        if not (200 <= speed <= 40000):
            raise ValueError("speed 必须在 200~40000 之间")
        if not hasattr(gesture, "steps"):
            raise AttributeError(f"'{type(gesture).__name__}' object has no attribute 'to_pointer_matrix'")
        self._gestures_to_pointer_action([gesture], speed=speed)

    # ==================== shell-backed bridge ====================

    def wake_up_display(self):
        self._arkuix_driver.wake_up_display()

    def close_display(self):
        self._arkuix_driver.close_display()

    def is_display_on(self):
        return self._arkuix_driver.is_display_on()

    def is_display_locked(self):
        return self._arkuix_driver.is_display_locked()

    def press_home(self):
        self._arkuix_driver.press_home()

    def go_home(self):
        self._arkuix_driver.go_home()

    def press_power(self):
        self._arkuix_driver.press_power()

    def shell(self, cmd, timeout=60):
        return self._arkuix_driver.shell(cmd, timeout)

    def get_language(self):
        return self._arkuix_driver.get_language()

    # ==================== internal helpers ====================

    def _to_on_dict(self, selector) -> dict:
        """Convert a BY selector / dict / string to a dict for ArkUIXDriver."""
        if isinstance(selector, dict):
            return selector
        if isinstance(selector, str):
            return {"text": selector}
        if hasattr(selector, '_sourcing_call'):
            return _on_dict_from_selector(selector)
        return None

    def close(self):
        """Disconnect from the socket server and release USB forwarding."""
        self._arkuix_driver.close()
