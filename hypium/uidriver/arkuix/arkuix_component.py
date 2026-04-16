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
ArkUI-X cross-platform component wrapper.

Wraps a component returned by the ArkUI-X UiTestSocketServer's
FindComponent / FindComponents commands. Component operations are
sent back to the server via the socket client using integer command codes.

Protocol: Server identifies components by componentId (the .id() attribute
set in ArkTS). There is no server-side session management — each operation
re-finds the component by its componentId.

Works identically for iOS and Android ArkUI-X applications.
"""

import logging
from typing import Optional, Dict, Any
from hypium.model.basic_data_type import Rect

logger = logging.getLogger("hypium.arkuix")

class SocketCommand:
    """Integer command codes matching C++ SocketCommand enum in socket_request.h."""
    # Component commands (1-24)
    COMPONENT_CLICK = 1
    COMPONENT_DOUBLE_CLICK = 2
    COMPONENT_LONG_CLICK = 3
    COMPONENT_GET_ID = 4
    COMPONENT_GET_TEXT = 5
    COMPONENT_GET_TYPE = 6
    COMPONENT_IS_CLICKABLE = 7
    COMPONENT_IS_LONG_CLICKABLE = 8
    COMPONENT_IS_SCROLLABLE = 9
    COMPONENT_IS_ENABLED = 10
    COMPONENT_IS_FOCUSED = 11
    COMPONENT_IS_SELECTED = 12
    COMPONENT_IS_CHECKED = 13
    COMPONENT_IS_CHECKABLE = 14
    COMPONENT_INPUT_TEXT = 15
    COMPONENT_CLEAR_TEXT = 16
    COMPONENT_SCROLL_TO_TOP = 17
    COMPONENT_SCROLL_TO_BOTTOM = 18
    COMPONENT_GET_BOUNDS = 19
    COMPONENT_GET_BOUNDS_CENTER = 20
    COMPONENT_PINCH_OUT = 21
    COMPONENT_PINCH_IN = 22
    COMPONENT_GET_COMPONENT_INFO = 23
    COMPONENT_SCROLL_SEARCH = 24

    # Driver commands (100+)
    DRIVER_DELAY_MS = 100
    DRIVER_PRESS_BACK = 101
    DRIVER_ASSERT_COMPONENT_EXIST = 102
    DRIVER_TRIGGER_KEY = 103
    DRIVER_TRIGGER_COMBINE_KEYS = 104
    DRIVER_INJECT_MULTI_POINTER_ACTION = 105
    DRIVER_CLICK = 106
    DRIVER_DOUBLE_CLICK = 107
    DRIVER_LONG_CLICK = 108
    DRIVER_SWIPE = 109
    DRIVER_FLING_DIRECTION = 110
    DRIVER_FIND_COMPONENT = 111
    DRIVER_FIND_COMPONENTS = 112
    DRIVER_GET_DISPLAY_SIZE = 113
    DRIVER_FLING_POINT = 114
    DRIVER_DRAG = 115
    DRIVER_SET_DISPLAY_ROTATION = 116

class ArkUIXComponent:
    """
    Represents an ArkUI component found on the device.
    All operations are forwarded to the C++ side via socket commands.

    The server identifies components by componentId (the .id() value set in ArkTS).
    Each operation sends the componentId so the server can re-find and operate on
    the component.

    Attributes:
        component_id: The component's id attribute (used by server to find it)
        info: Component info dict (text, type, componentId, bounds, etc.)
    """

    def __init__(self, client, component_id: str, info: Dict[str, Any]):
        """
        Args:
            client: ArkUIXSocketClient instance
            component_id: Component id (matches .id() in ArkTS)
            info: Component info dict from server (ComponentInfo JSON)
        """
        self._client = client
        self._component_id = component_id
        self._info = info or {}

    @property
    def component_id(self) -> str:
        return self._component_id

    def _send(self, command: int, extra_params: dict = None) -> Any:
        """Send a component command with componentId."""
        params = {"componentId": self._component_id}
        if extra_params:
            params.update(extra_params)
        logger.debug("_send: cmd=%s, params=%s", command, params)
        result = self._client.send_command(command, params)
        logger.debug("_send: cmd=%s returned: %r", command, result)
        return result

    # ==================== Actions ====================

    def click(self):
        """点击该控件"""
        self._send(SocketCommand.COMPONENT_CLICK)

    def double_click(self):
        """双击该控件"""
        self._send(SocketCommand.COMPONENT_DOUBLE_CLICK)

    def long_click(self):
        """长按该控件"""
        self._send(SocketCommand.COMPONENT_LONG_CLICK)

    def input_text(self, text: str):
        """
        向该控件输入文本
        @param text: 需要输入的文本内容
        """
        self._send(SocketCommand.COMPONENT_INPUT_TEXT, {"text": text})

    def scroll_search(self, on: dict) -> Optional['ArkUIXComponent']:
        """
        在可滚动控件中搜索目标控件。

        @param on: 搜索条件dict (e.g. {"componentId": "targetBtn"})
        @return: 找到的组件或None
        """
        result = self._send(SocketCommand.COMPONENT_SCROLL_SEARCH, {"targetOn": on})
        if result and isinstance(result, dict):
            component_id = result.get("componentId")
            return ArkUIXComponent(self._client, component_id, result)
        return None

    # ==================== Properties ====================

    def get_text(self) -> str:
        """获取控件文本"""
        result = self._send(SocketCommand.COMPONENT_GET_TEXT)
        # Server returns string directly as result
        return str(result) if result is not None else ""

    def get_id(self) -> str:
        """获取控件ID"""
        result = self._send(SocketCommand.COMPONENT_GET_ID)
        return str(result) if result is not None else ""

    def get_type(self) -> str:
        """获取控件类型"""
        result = self._send(SocketCommand.COMPONENT_GET_TYPE)
        return str(result) if result is not None else ""

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _rect_from_dict(cls, data: Dict[str, Any]) -> Rect:
        """将服务端返回的位置信息转换为 Rect。"""
        left = cls._safe_int(data.get("left", 0))
        top = cls._safe_int(data.get("top", 0))

        if "right" in data or "bottom" in data:
            right = cls._safe_int(data.get("right", left))
            bottom = cls._safe_int(data.get("bottom", top))
        else:
            width = cls._safe_int(data.get("width", 0))
            height = cls._safe_int(data.get("height", 0))
            right = left + width
            bottom = top + height

        return Rect(left, right, top, bottom)

    def get_component_info(self) -> dict:
        """获取完整的组件信息"""
        result = self._send(SocketCommand.COMPONENT_GET_COMPONENT_INFO)
        return result if isinstance(result, dict) else {}

    def get_bounds(self) -> Rect:
        """获取组件边界信息"""
        result = self._send(SocketCommand.COMPONENT_GET_BOUNDS)
        return self._rect_from_dict(result) if isinstance(result, dict) else Rect(0, 0, 0, 0)

    def get_bounds_center(self) -> tuple:
        """获取组件边界中心点坐标"""
        result = self._send(SocketCommand.COMPONENT_GET_BOUNDS_CENTER)
        if isinstance(result, dict):
            return (self._safe_int(result.get("x", 0)), self._safe_int(result.get("y", 0)))
        bounds = self.get_bounds()
        return ((bounds.left + bounds.right) // 2, (bounds.top + bounds.bottom) // 2)

    def is_clickable(self) -> bool:
        """是否可点击"""
        result = self._send(SocketCommand.COMPONENT_IS_CLICKABLE)
        # Server returns boolean directly
        return bool(result)

    def is_long_clickable(self) -> bool:
        """是否可长按"""
        result = self._send(SocketCommand.COMPONENT_IS_LONG_CLICKABLE)
        return bool(result)

    def is_scrollable(self) -> bool:
        """是否可滚动"""
        result = self._send(SocketCommand.COMPONENT_IS_SCROLLABLE)
        return bool(result)

    def is_enabled(self) -> bool:
        """是否启用"""
        result = self._send(SocketCommand.COMPONENT_IS_ENABLED)
        return bool(result)

    def is_focused(self) -> bool:
        """是否聚焦"""
        result = self._send(SocketCommand.COMPONENT_IS_FOCUSED)
        return bool(result)

    def is_selected(self) -> bool:
        """是否选中"""
        result = self._send(SocketCommand.COMPONENT_IS_SELECTED)
        return bool(result)

    def is_checked(self) -> bool:
        """是否勾选"""
        result = self._send(SocketCommand.COMPONENT_IS_CHECKED)
        return bool(result)

    def is_checkable(self) -> bool:
        """是否可勾选"""
        result = self._send(SocketCommand.COMPONENT_IS_CHECKABLE)
        return bool(result)

    # ==================== Cached info access ====================

    @property
    def text(self) -> str:
        """从缓存的 info 中获取文本（不发送网络请求）"""
        return self._info.get("text", "")

    @property
    def type(self) -> str:
        return self._info.get("type", "")

    @property
    def compid(self) -> str:
        return self._info.get("componentId", "")

    def getBounds(self) -> Rect:
        """兼容 OHOSDriver 的 getBounds 方法"""
        return self.get_bounds()

    def getText(self) -> str:
        """兼容 OHOSDriver 的 getText 方法"""
        return self.get_text()

    def getId(self) -> str:
        """兼容 OHOSDriver 的 getId 方法"""
        return self.get_id()

    def getType(self) -> str:
        """兼容 OHOSDriver 的 getType 方法"""
        return self.get_type()

    def getBoundsCenter(self) -> tuple:
        """兼容 OHOSDriver 的 getBoundsCenter 方法"""
        return self.get_bounds_center()

    def __repr__(self):
        return (f"ArkUIXComponent(component_id={self._component_id!r}, "
                f"type={self._info.get('type', '?')!r}, "
                f"text={self._info.get('text', '')!r})")
