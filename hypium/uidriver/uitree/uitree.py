import json
import re
import shutil
import time
import os
import traceback
from dataclasses import dataclass
from typing import Union, List, Optional
from hypium.model import KeyCode, FormatString
from hypium.model.driver_config import ClearTextMode
from hypium.uidriver.uitree.page import Page
from hypium.utils.logger import basic_log
from hypium.utils import utils, timer
from hypium.utils.typevar import T
from hypium.exception import *
from hypium.uidriver.interface.uitree import IUiComponent, ISelector
from hypium.uidriver.interface.atomic_driver import IAtomicDriver, IComponentFinder
from hypium.model.basic_data_type import Rect, Point, JsonBase, InputTextMode
from hypium.uidriver.by import By, MatchPattern
from hypium.utils.retry_utils import support_retry


def normalize_match_pattern(match_pattern: Union[MatchPattern, str]):
    if isinstance(match_pattern, MatchPattern):
        match_pattern_str = convert_match_pattern(match_pattern)
    elif isinstance(match_pattern, str):
        match_pattern_str = match_pattern
    else:
        raise TypeError("Invalid match_pattern type: %s" % type(match_pattern))
    return match_pattern_str


def convert_match_pattern(value: MatchPattern):
    if value == MatchPattern.EQUALS or value is None:
        return "equals"
    elif value == MatchPattern.STARTS_WITH:
        return "starts_with"
    elif value == MatchPattern.ENDS_WITH:
        return "ends_with"
    elif value == MatchPattern.CONTAINS:
        return "contains"
    elif value == MatchPattern.REGEXP:
        return "regexp"
    elif value == MatchPattern.REGEXP_ICASE:
        return "regexp_ignore_case"
    else:
        raise TypeError("Invalid match pattern: " + str(value))


def normalize_lxml_attribute_to_str(data):
    if isinstance(data, list):
        data_normalized = data[0]
    else:
        data_normalized = data
    if not isinstance(data_normalized, str):
        data_normalized = str(data_normalized)
    return data_normalized


def fuzzy_match(lxml_ctx, src_text, target_text, match_pattern):
    src_text = normalize_lxml_attribute_to_str(src_text)
    target_text = normalize_lxml_attribute_to_str(target_text)
    result = TextMatcher(src_text, match_pattern).match(target_text)
    return result


def register_fuzzy_match_to_lxml():
    try:
        from hypium.utils import xml_builder
        xml_builder.register_xpath_custom_func("fuzzy_match", fuzzy_match)
    except ImportError:
        basic_log.warning("Fail to import lxml, please install lxml")


# 注册xpath扩展匹配函数
register_fuzzy_match_to_lxml()


class TextMatcher:

    def __init__(self, value, match_pattern="equals"):
        self.value = value
        if isinstance(match_pattern, MatchPattern):
            normalized_match_pattern = convert_match_pattern(match_pattern)
        elif match_pattern is None:
            normalized_match_pattern = "equals"
        else:
            normalized_match_pattern = match_pattern
        self.match_pattern = normalized_match_pattern

    def match(self, value):
        if self.match_pattern == "contains":
            if self.value in value:
                return True
            else:
                return False
        elif self.match_pattern == "starts_with":
            if value.startswith(self.value):
                return True
            else:
                return False
        elif self.match_pattern == "ends_with":
            if value.endswith(self.value):
                return True
            else:
                return False
        elif self.match_pattern == "equals":
            if value == self.value:
                return True
            else:
                return False
        elif self.match_pattern == "regexp":
            result = re.search(self.value, value)
            return False if result is None else True
        elif self.match_pattern.startswith("fuzzy"):
            import difflib
            similarity = 0.8
            result = self.match_pattern.split("#")
            if len(result) == 2:
                similarity = utils.parse_float(result[1], 0.8)
            return difflib.SequenceMatcher(a=self.value, b=value).ratio() >= similarity
        elif self.match_pattern == "regexp_ignore_case":
            result = re.search(self.value, value, re.IGNORECASE)
            return False if result is None else True
        else:
            raise RuntimeError("Invalid match pattern")

    def __eq__(self, other):
        return self.match(other)

    def __str__(self):
        return "%s@%s" % (self.value, self.match_pattern)

    def __repr__(self):
        return self.__str__()


class BoolMatcher:

    def __init__(self, value):
        if isinstance(value, bool):
            self.bool_value = value
        elif isinstance(value, str):
            if value.lower() == "false":
                self.bool_value = False
            elif value.lower() == "true":
                self.bool_value = True
            else:
                self.bool_value = False
        else:
            self.bool_value = False
        self.org_value = value

    def __eq__(self, other):
        other = BoolMatcher(other)
        return self.bool_value == other.bool_value

    def __str__(self):
        return "%s[%s]" % (self.bool_value, self.org_value)


@dataclass
class UiTreeDumpConfig:
    """控件dump模式配置"""
    window_id: int = None
    bundle_name: str = None
    display_id: int = -1  # -1表示未指定display_id


def by(func: T) -> T:
    func_name = func.__name__

    def wrapper(self, *args, **kwargs):
        if getattr(self, "_xpath"):
            raise ValueError("xpath can't used with other attribute selector")
        self.matcher[func_name] = TextMatcher(*args, **kwargs)
        return self

    return wrapper


def by_bool(func: T) -> T:
    func_name = func.__name__

    def wrapper(self, value):
        self.matcher[func_name] = BoolMatcher(value)
        return self

    return wrapper


class BySelector(ISelector):

    def __init__(self):
        self.matcher = {}
        self.match_index = 0
        self._current_match_index = 0
        self._xpath = None
        self._abspath = None
        self._config = {}
        self._image = None
        self._target_description = ""
        self._before_selector = None
        self._after_selector = None
        self._display_id = -1
        self._pos = None

    def reset_matcher(self):
        self._current_match_index = self.match_index

    def match(self, node):
        if "attributes" in node.keys():
            node = node["attributes"]
        else:
            return False
        for item in self.matcher.keys():
            if item not in node.keys():
                return False
            if self.matcher[item] == node[item]:
                continue
            else:
                return False
        if self._current_match_index <= 0:
            return True
        else:
            self._current_match_index -= 1
            return False

    def set_config(self, config_name, config_value):
        self._config[config_name] = config_value
        return self

    def get_config(self, config_name, default_value=""):
        return self._config.get(config_name, default_value)

    def update_config(self, config: dict):
        self._config.update(config)
        return self

    def xpath(self, xpath):
        if self._xpath:
            raise ValueError("xpath already set to %s, can't set again" % self._xpath)
        if self.matcher:
            raise ValueError("xpath can't used with other attribute selector")
        self._xpath = xpath
        return self

    def abspath(self, abspath):
        """
        @func 使用控件全路径来查找控件
        @param abspath: UiViewer插件生成的非标准控件path, 注意ui结构变化后容易发生变化
        """
        if self._xpath:
            raise ValueError("abspath already set to %s, can't set again" % self._xpath)
        if self.matcher:
            raise ValueError("abspath can't used with other attribute selector")
        self._abspath = abspath
        return self

    @by
    def key(self, value, match_pattern: str):
        """
        @func 通过key查询控件
        @param value: 期望的控件key值
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
        """
        pass

    @by
    def text(self, value, match_pattern: str):
        """
        @func 通过text查询控件
        @param value: 期望的控件key值
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
        """
        pass

    @by
    def type(self, value, match_pattern: str):
        """
        @func 通过type查询控件
        @param value: 期望的控件key值
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
        """
        pass

    def index(self, value: int):
        """
        @func 匹配目标的索引序号, 从0开始
        @param value: 匹配目标的索引序号
        """
        if type(value) != int or value < 0:
            raise HypiumParamError(msg="invalid index, expect integer > 0, get %s" % str(value))
        self.match_index = value
        return self

    @by
    def hierarchy(self, value, match_pattern: str):
        """
        @func 通过hierarchy查询控件
        @param value: 期望的控件hierarchy值
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
                      "regexp_ignore_case" 忽略大小写进行正则匹配
        """
        pass

    @by
    def description(self, value, match_pattern: str):
        """
        @func 通过description查询控件
        @param value: 期望的控件description值
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
                      "regexp_ignore_case" 忽略大小写进行正则匹配
        """
        pass

    @by
    def hint(self, value, match_pattern: str):
        """
        @func 通过hint属性查询控件
        @param value: 期望的控件hint值
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
                      "regexp_ignore_case" 忽略大小写进行正则匹配
        """
        pass

    @by_bool
    def clickable(self, value):
        """
        @func 通过clickable查询控件
        @param value: 目标控件的clickable属性值
        """
        pass

    @by_bool
    def scrollable(self, value) -> bool:
        """
        @func 通过scrollable查询控件
        @param value: 目标控件的scrollable属性值
        """
        pass

    @by_bool
    def enabled(self, value) -> bool:
        """
        @func 通过enabled查询控件
        @param value: 目标控件的enable属性值
        """
        pass

    @by_bool
    def focused(self, value) -> bool:
        """
        @func 通过focused查询控件
        @param value: 目标控件的focused属性值
        """
        pass

    @by_bool
    def longClickable(self, value):
        """
        @func 通过longClickable查询控件
        @param value: 目标控件的longClickable属性值
        """
        pass

    @by_bool
    def checked(self, value):
        """
        @func 通过checked查询控件
        @param value: 目标控件的checked属性值
        """
        pass

    @by_bool
    def checkable(self, value):
        """
        @func 通过checkable查询控件
        @param value: 目标控件的checkable属性值
        """
        pass

    @by_bool
    def selected(self, value):
        """
        @func 通过selected查询控件
        @param value: 目标控件的selected属性值
        """
        pass

    def image(self, image_path: str, similarity=0.8):
        """
        @func 根据图片匹配
        """
        self._image = utils.cv_imread(image_path)
        self._image_similarity = similarity
        self._image_path = image_path
        return self

    def target(self, target_description: str):
        if not target_description:
            raise ValueError("description can't be null")
        self._target_description = target_description
        return self

    def custom_attr(self, attr_name, value, match_pattern="equals"):
        """
        @func 通过自定义属性查询控件
        @param match_pattern: 匹配模式，支持
                      "equals" 全等匹配
                      "starts_with" 前缀匹配
                      "ends_with" 后缀匹配
                      "contains" 包含匹配
                      "regexp" 正则表达式匹配
        """
        self.matcher[attr_name] = TextMatcher(value, match_pattern)
        return self

    def isBefore(self, selector):
        if isinstance(selector, BySelector):
            self._before_selector = selector
        else:
            self._before_selector = BySelector.from_by(selector)
        return self

    def isAfter(self, selector):
        if isinstance(selector, BySelector):
            self._after_selector = selector
        else:
            self._after_selector = BySelector.from_by(selector)
        return self

    def inDisplay(self, display_id: int):
        """
        @func 在指定的屏幕中查找控件
        @param display_id: 屏幕id
        """
        self._display_id = display_id
        return self

    @classmethod
    def from_by(cls, arkui_by: By):
        cur_by = arkui_by
        uitree_by = BySelector()
        while cur_by is not None and "seed" not in cur_by._backend_obj_ref:
            if cur_by._sourcing_call is not None:
                next_by, matcher_name, matcher_value = cur_by._sourcing_call
                matcher_name = matcher_name.split('.')[1]
                matcher_value = matcher_value.copy()
                if len(matcher_value) > 1:
                    matcher_value[1] = convert_match_pattern(matcher_value[1])
                if matcher_name == "key" or matcher_name == "id":
                    uitree_by.key(*matcher_value)
                elif matcher_name == "text":
                    uitree_by.text(*matcher_value)
                elif matcher_name == "type":
                    uitree_by.type(*matcher_value)
                elif matcher_name == "checkable":
                    uitree_by.checkable(*matcher_value)
                elif matcher_name == "longClickable":
                    uitree_by.longClickable(*matcher_value)
                elif matcher_name == "clickable":
                    uitree_by.clickable(*matcher_value)
                elif matcher_name == "scrollable":
                    uitree_by.scrollable(*matcher_value)
                elif matcher_name == "enabled":
                    uitree_by.enabled(*matcher_value)
                elif matcher_name == "focused":
                    uitree_by.focused(*matcher_value)
                elif matcher_name == "selected":
                    uitree_by.selected(*matcher_value)
                elif matcher_name == "checked":
                    uitree_by.checked(*matcher_value)
                elif matcher_name == "isBefore":
                    uitree_by.isBefore(*matcher_value)
                elif matcher_name == "isAfter":
                    uitree_by.isAfter(*matcher_value)
                elif matcher_name == "description":
                    uitree_by.description(*matcher_value)
                elif matcher_name == "hint":
                    uitree_by.hint(*matcher_value)
                elif matcher_name == "inDisplay":
                    uitree_by.inDisplay(*matcher_value)
                else:
                    raise ValueError("Not support [BY.%s] in uitree mode" % matcher_name)
                if next_by == cur_by:
                    break
                cur_by = next_by
            else:
                cur_by = None
        return uitree_by

    def __str__(self):
        if self._xpath:
            return str(self._xpath)
        if self._target_description:
            return "AITarget[%s]" % self._target_description
        if self._abspath:
            return str(self._abspath)
        msg = str(self.matcher)
        if self._image is not None:
            msg += "[%s#%s]" % (self._image_path, self._image_similarity)
        return msg

    def __repr__(self):
        return self.__str__()


def parse_bounds(bounds_str):
    result = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
    if result is not None:
        groups = result.groups()
        return (int(groups[0]), int(groups[1])), (int(groups[2]), int(groups[3]))
    return (0, 0), (0, 0)


class ComponentOperationMixIn:
    """
    @inner 实现控件支持的操作
    """

    def clearText(self):
        if len(self.text) <= 0:
            self.driver.click(*self.center)
            time.sleep(0.8)
            return
        if self.driver.config.clear_text_mode == ClearTextMode.ONCE:
            self._clearText_by_combination_code()
        else:
            self._clearText_old_way()

    def _clearText_by_combination_code(self):
        self.driver.click(*self.center)
        time.sleep(0.8)
        self.driver.triggerCombineKeys(KeyCode.CTRL_LEFT.value, KeyCode.A.value)
        time.sleep(0.8)
        self.driver.triggerKey(KeyCode.DEL.value)
        time.sleep(0.8)

    def _clearText_old_way(self):
        """
        @func 清空输入框
        """
        self.driver.click(*self.center)
        time.sleep(0.8)
        for _ in range(len(self.text)):
            self.driver.triggerKey(KeyCode.DPAD_RIGHT)
        for _ in range(len(self.text)):
            self.driver.triggerKey(KeyCode.DEL)

    def inputText(self, text, mode: InputTextMode = None):
        """
        @func 输入文本
        @param text: 输入的文本
        @param mode: 输入文本的模式
        """
        addition = False
        if isinstance(mode, InputTextMode) and mode._data.get("addition") is True:
            addition = mode._data.get("addition")
            if addition is None:
                addition = self.driver.config.clear_text_before_input

        if addition:
            self.driver.click(*self.center)
            time.sleep(0.8)
            self.driver.triggerKey(KeyCode.MOVE_END)
            time.sleep(0.8)
        else:
            self.clearText()
        # 输入内容
        out_of_screen_x, out_of_screen_y = self.driver.config._out_of_screen_coord_for_input_text
        self.driver.inputText(Point(out_of_screen_x, out_of_screen_y), text, mode)

    def scrollSearch(self, selector: BySelector, direction="UP", deadzone_ratio=0.25, times=10, speed=600):
        rect = self.getBounds()
        left, right, top, bottom = rect
        w, h = rect.get_size()
        if direction == "UP":
            start_x = left + 0.5 * w
            start_y = top + (1 - deadzone_ratio) * h
            end_x = start_x
            end_y = top + deadzone_ratio * h
        elif direction == "DOWN":
            start_x = left + 0.5 * w
            start_y = top + deadzone_ratio * h
            end_x = start_x
            end_y = top + (1 - deadzone_ratio) * h
        elif direction == "LEFT":
            start_x = left + (1 - deadzone_ratio) * w
            start_y = top + h * 0.5
            end_x = left + deadzone_ratio * w
            end_y = start_y
        elif direction == "RIGHT":
            start_x = left + deadzone_ratio * w
            start_y = top + h * 0.5
            end_x = left + (1 - deadzone_ratio) * w
            end_y = start_y
        else:
            raise ValueError("Invalid direction [%s], direction can only [UP, DOWN, LEFT, RIGHT]" % direction)

        for _ in range(times):
            comp = UiTree(self.driver).find_component(selector, timeout=0)
            if comp:
                return comp
            start_x, start_y, end_x, end_y = map(int, (start_x, start_y, end_x, end_y))
            self.driver.swipe(start_x, start_y, end_x, end_y, speed)
            time.sleep(0.8)
        return None


class UiWidget(ComponentOperationMixIn, IUiComponent):
    def __init__(self, node, hierarchy, driver, bounds=None):
        self.driver = driver
        self.raw_node = node
        self.hierarchy = hierarchy
        if "attributes" in node:
            attr = node["attributes"]
        else:
            attr = node
        if isinstance(bounds, Rect):
            self.bounds = bounds
        else:
            self.bounds = parse_bounds(attr["bounds"])
            self.bounds = Rect.from_tuple(*self.bounds)
        self.center = self.bounds.get_center()
        self.text = attr.get("text", "")
        self.id = attr.get("id", "")
        self.checked = attr.get("checked", "")
        self.checkable = attr.get("checkable", "")
        self.enabled = attr.get("enabled", "")
        self.clickable = attr.get("clickable", "")
        self.longClickable = attr.get("longClickable", "")
        self.selected = attr.get("selected", "")
        self.focused = attr.get("focused", "")
        self.attr = attr

    def __getattr__(self, item):
        result = self.attr.get(item, None)
        if result is None:
            raise AttributeError("%s has no attribute [%s]" % (self.__class__.__name__, item))
        if item.endswith("ed") or item.endswith("ble"):
            # 类似checked和clickable这类属性转换为bool变量
            if result == "false":
                return False
            elif result == "true":
                return True
        return result

    def click(self) -> None:
        """
        @func:实现相对路径控件点击
        @return: None
        @example # 查找文本为"打开"的控件
                 item = driver.UiTree.find_component(BySelector().text("打开"))
                 # 点击控件
                 item.click()
        """
        self.driver.click(self.center[0], self.center[1])

    def doubleClick(self) -> None:
        """
        @func:实现相对路径控件双击
        @example # 查找文本为"打开"的控件
                     item = driver.UiTree.find_component(BySelector().text("打开"))
                     # 双击控件
                     item.doubleClick()
        """
        self.driver.doubleClick(self.center[0], self.center[1])

    def longClick(self) -> None:
        """
        @func:实现相对路径控件长按
        @example # 查找文本为"打开"的控件
                         item = driver.UiTree.find_component(BySelector().text("打开"))
                         # 长按控件
                         item.longClick()
        """
        self.driver.longClick(self.center[0], self.center[1])

    def double_click(self):
        self.doubleClick()

    def long_click(self):
        self.longClick()

    def getId(self) -> str:
        """
        @func 获取控件id
        @return: 在api8之前返回系统为控件分配的数字id，在api9以及之后返回用户为控件设置的id
        """
        return self.attr.get("id", "")

    def getKey(self) -> str:
        """
        @func: 获取用户设置的控件id值，该接口在api9之上被删除，使用getId()替换
        @return: 用户设置的控件id值
        """
        return self.attr.get("id", "")

    def getText(self) -> str:
        """
        @func 获取控件text属性内容
        """
        return self.attr.get("text", "")

    def getType(self) -> str:
        """
        @func 获取控件type属性内容
        """
        return self.attr.get("type", "")

    def isClickable(self) -> bool:
        """
        @func 获取控件clickable属性内容
        """
        return self.attr.get("clickable", "") == "true"

    def isScrollable(self) -> bool:
        """
        @func 获取控件scrollable属性内容
        """
        return self.attr.get("scrollable", "") == "true"

    def isEnabled(self) -> bool:
        """
        @func 获取控件enabled属性内容
        """
        return self.attr.get("enabled", "") == "true"

    def isFocused(self) -> bool:
        """
        @func 获取控件focused属性内容
        """
        return self.attr.get("focused", "") == "true"

    def isLongClickable(self):
        """
        @func 获取控件longClickable属性内容
        """
        return self.attr.get("longClickable", "") == "true"

    def isChecked(self):
        """
        @func 获取控件checked属性内容
        """
        if "state" in self.attr:
            return self.attr["state"]
        else:
            return self.attr.get("checked", "") == "true"

    def isCheckable(self):
        """
        @func 获取控件checkable属性内容
        """
        return self.attr.get("checkable", "") == "true"

    def isSelected(self):
        """
        @func 获取控件selected属性内容
        """
        return self.attr.get("selected", "") == "true"

    def getDescription(self) -> str:
        """
        @func 获取控件description属性内容
        """
        return self.attr.get("description", "")

    def getBounds(self) -> Rect:
        """
        @func 获取控件边框位置
        @return 表示控件边框位置的Rect对象, 可访问该对象的left/right/top/bottom属性获取边框位置
        """
        return self.bounds

    def getBoundsCenter(self) -> Point:
        return Point(*self.center)

    def getAllProperties(self) -> JsonBase:
        result = JsonBase.from_dict(self.raw_node.get("attributes", {}))
        setattr(result, "bounds", {"left": self.bounds.left, "top": self.bounds.top,
                                   "right": self.bounds.right, "bottom": self.bounds.bottom})
        return result

    def _find_component(self, selector):
        """
        查找匹配的子节点
        """
        tree = UiTree(self.driver)
        return tree._find_component(selector, self.raw_node, self.hierarchy)

    def _find_all_components(self, selector):
        """
        查找所有匹配的子节点
        """
        tree = UiTree(self.driver)
        matched_comps = []
        tree._find_all_components(selector, self.raw_node, self.hierarchy, matched_comps)
        return matched_comps

    def getHint(self) -> str:
        """
        @func 获取控件type属性内容
        """
        return self.attr.get("hint", "")

    def __str__(self):
        text_info_len = min(10, len(self.text))
        text_info = self.text[0:text_info_len]
        return f"{self.getType()}#{self.center}#{self.id}#{text_info}#U"

    def __repr__(self):
        return self.__str__()

    @classmethod
    def from_coordinate(cls, driver, x, y):
        return cls({"attributes": {"bounds": "[%s,%s][%s,%s]" % (x, y, x, y)}}, "", driver)


class XpathWidget(ComponentOperationMixIn, IUiComponent):
    def __init__(self, node, hierarchy, driver):
        self.driver = driver
        self.raw_node = node
        self.hierarchy = hierarchy
        attr = node.attrib
        self.bounds = parse_bounds(attr["bounds"])
        self.bounds = Rect.from_tuple(*self.bounds)
        self.center = self.bounds.get_center()
        self.text = attr.get("text", "")
        self.id = attr.get("id", "")
        self.checked = attr.get("checked", "")
        self.checkable = attr.get("checkable", "")
        self.enabled = attr.get("enabled", "")
        self.clickable = attr.get("clickable", "")
        self.longClickable = attr.get("longClickable", "")
        self.selected = attr.get("selected", "")
        self.focused = attr.get("focused", "")
        self.attr = attr

    def getId(self) -> str:
        """
        @func 获取控件id
        @return: 在api8之前返回系统为控件分配的数字id，在api9以及之后返回用户为控件设置的id
        """
        return self.attr.get("id", "")

    def getKey(self) -> str:
        """
        @func: 获取用户设置的控件id值，该接口在api9之上被删除，使用getId()替换
        @return: 用户设置的控件id值
        """
        return self.attr.get("id", "")

    def getText(self) -> str:
        """
        @func 获取控件text属性内容
        """
        return self.attr.get("text", "")

    def getType(self) -> str:
        """
        @func 获取控件type属性内容
        """
        return self.attr.get("type", "")

    def isClickable(self) -> bool:
        """
        @func 获取控件clickable属性内容
        """
        return self.attr.get("clickable", "") == "true"

    def isScrollable(self) -> bool:
        """
        @func 获取控件scrollable属性内容
        """
        return self.attr.get("scrollable", "") == "true"

    def isEnabled(self) -> bool:
        """
        @func 获取控件enabled属性内容
        """
        return self.attr.get("enabled", "") == "true"

    def isFocused(self) -> bool:
        """
        @func 获取控件focused属性内容
        """
        return self.attr.get("focused", "") == "true"

    def isLongClickable(self):
        """
        @func 获取控件longClickable属性内容
        """
        return self.attr.get("longClickable", "") == "true"

    def isChecked(self):
        """
        @func 获取控件checked属性内容
        """
        return self.attr.get("checked", "") == "true"

    def isCheckable(self):
        """
        @func 获取控件checkable属性内容
        """
        return self.attr.get("checkable", "") == "true"

    def isSelected(self):
        """
        @func 获取控件selected属性内容
        """
        return self.attr.get("selected", "") == "true"

    def getDescription(self) -> str:
        """
        @func 获取控件description属性内容
        """
        return self.attr.get("description", "")

    def getBounds(self) -> Rect:
        """
        @func 获取控件边框位置
        @return 表示控件边框位置的Rect对象, 可访问该对象的left/right/top/bottom属性获取边框位置
        """
        return self.bounds

    def getAllProperties(self) -> JsonBase:
        result = JsonBase.from_dict(self.attr)
        setattr(result, "bounds", {"left": self.bounds.left, "top": self.bounds.top,
                                   "right": self.bounds.right, "bottom": self.bounds.bottom})
        return result

    def getBoundsCenter(self) -> Point:
        return Point(*self.center)

    def click(self) -> None:
        """
        @func:实现xpath路径控件点击
        @return: None
        @example # 查找文本为"备忘录"的控件
                 item = driver.UiTree.find_by_xpath("//Text[@text='备忘录']")
                 # 点击控件
                 item.click()
        """
        self.driver.click(self.center[0], self.center[1])

    def doubleClick(self) -> None:
        """
        @func:实现xpath路径控件双击
        @example # 查找文本为"备忘录"的控件
                 item = driver.UiTree.find_by_xpath("//Text[@text='备忘录']")
                 # 双击控件
                 item.doubleClick()
        """
        self.driver.doubleClick(self.center[0], self.center[1])

    def longClick(self) -> None:
        """
        @func:实现xpath路径控件长按
        @example # 查找文本为"备忘录"的控件
                 item = driver.UiTree.find_by_xpath("//Text[@text='备忘录']")
                 # 长按控件
                 item.longClick()
        """
        self.driver.longClick(self.center[0], self.center[1])

    def double_click(self):
        self.doubleClick()

    def long_click(self):
        self.longClick()

    def getHint(self) -> str:
        """
        @func 获取控件hint属性内容
        """
        return self.attr.get("hint", "")

    def __str__(self):
        text_info_len = min(10, len(self.text))
        text_info = self.text[0:text_info_len]
        return f"{self.getType()}#{self.center}#{self.id}#{text_info}#X"

    def __repr__(self):
        return self.__str__()


def escape_char(raw_string):
    """转换xml中需要转义的字符"""
    return raw_string.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;").replace("'", "&apos;").replace(
        "\"", "&quot;")


def _json_to_xml_node(node_dict):
    """
    转换json中的子节点
    """
    if isinstance(node_dict, str):
        return "<{tag}>{value}</{tag}>".format(tag=node_dict.get("type", "node"), value=node_dict)
    attrs = node_dict.get("attributes")
    tag = attrs.get("type", "node")
    attrs = {attr: attrs.get(attr) for attr in attrs if attr not in {"type", "children"}}
    if "value" in node_dict:
        xml_str = "<{tag} {attrs}>{value}</{tag}>".format(tag=tag, attrs=" ".join(
            '{}="{}"'.format(key, escape_char(val)) for key, val in attrs.items()), value=node_dict["value"])
    else:
        inner_xml = ''.join(_json_to_xml_node(child)
                            for child in node_dict.get("children", []))
        xml_str = "<{tag} {attrs}>{inner_xml}</{tag}>".format(tag=tag, attrs=" ".join(
            '{}="{}"'.format(key, escape_char(val)) for key, val in attrs.items()), inner_xml=inner_xml)
    return xml_str


def json_to_xml(json_str):
    """
    Convert json string to xml string.

    :param json_str: A json string.
    :return: An xml string.
    """
    if isinstance(json_str, str):
        try:
            json_dict = json.loads(json_str)
        except json.JSONDecodeError:
            return json_str
    else:
        json_dict = json_str
    attrs = json_dict.get("attributes")
    attrs = {attr: attrs.get(attr) for attr in attrs if attr not in {"type", "children"}}
    tag = attrs.get("type", "orgRoot")
    inner_xml = ''.join(_json_to_xml_node(child)
                        for child in json_dict.get("children", []))
    xml_str = "<{tag} {attrs}>{inner_xml}</{tag}>".format(tag=tag, attrs=" ".join(
        '{}="{}"'.format(key, escape_char(val)) for key, val in attrs.items()), inner_xml=inner_xml)
    return xml_str


def _convert_absolute_path(xpath: str):
    """
    json转换后存在一个虚拟的根节点, 如果使用绝对路径, 则需要拼装该根节点
    """
    if xpath.startswith("/") and not xpath.startswith("//"):
        return "/orgRoot" + xpath
    else:
        return xpath


class UiTree:
    """
    基于本地控件树的控件查找模块
    """

    def __init__(self, driver: IAtomicDriver):
        self.driver = utils.get_atomic_driver(driver)
        self.tree_file = ""
        self.tree = None
        self.xml_tree = None
        self.tmp_dir = os.path.abspath(utils.get_tmp_dir())
        self._widget_find_timeout = 3
        self._screenshot = None
        self._current_bundle_name = ""

    @property
    def device(self):
        return utils.get_device_from_object(self.driver)

    def refresh(self, retry_times=3, config=None):
        last_err = None
        for i in range(retry_times):
            try:
                return self._refresh(config=config)
            except Exception as e:
                self.driver.log_warning(f"Fail to dump layout [{e}], retry")
                last_err = e
                time.sleep(1)
        raise HypiumOperationFailError("Fail to get uitree, err:" + str(last_err))

    def _run_dump_command(self, uitest_command, config: UiTreeDumpConfig):
        """
        @param mode: default 默认控件获取模式, 获取所有窗口
                     window 仅获取指定窗口
        """
        if config.bundle_name is not None or config.window_id is not None:
            window_id = config.window_id
            bundle_name = config.bundle_name
            if window_id is not None:
                cmd = f"{uitest_command} dumpLayout -w {window_id}"
            else:
                cmd = f"{uitest_command} dumpLayout -b {bundle_name}"
        else:
            cmd = f"{uitest_command} dumpLayout"
        return self.device.execute_shell_command(cmd, timeout=20000)

    def _iterate_json_tree(self, node):
        if node is None:
            return
        yield node
        children = node.get("children")
        if not isinstance(children, list):
            return
        for child in children:
            for item in self._iterate_json_tree(child):
                yield item

    def _is_no_widget_window(self):
        """
        detect if window has no widget
        """
        count = 0
        for node in self._iterate_json_tree(self.tree):
            count += 1
            attributes = node.get("attributes", {})
            widget_type = attributes.get("type")
            if widget_type != "XComponent":
                continue
            if count > 100:
                return False
            left_top, right_bottom = parse_bounds(attributes.get("bounds"))
            bounds = Rect.from_tuple(left_top, right_bottom)
            width, height = bounds.get_size()
            if width > 400 and height > 400:
                return True
        return False

    def _dump_uitest_layout(self, tmp_tree_path, config):
        basename = utils.normalize_device_sn_to_filename(self.device.device_sn) + "_tmp_uitree.json"
        if tmp_tree_path is None:
            tmp_tree_path = os.path.join(self.tmp_dir, basename)
        tmp_tree_path = os.path.abspath(tmp_tree_path)
        # 移除存在的控件树文件, 避免使用旧数据
        if os.path.exists(tmp_tree_path):
            os.unlink(tmp_tree_path)
        uitest_command = self.driver.get_uitest_cmd()
        org_echo = self._run_dump_command(uitest_command, config)
        echo = utils.grep_one(org_echo, "DumpLayout saved to")
        if len(echo) == 0:
            raise HypiumOperationFailError(f"Fail to get uitree, err: {org_echo}")
        path_start = echo.find("/")
        if path_start <= 0:
            raise HypiumOperationFailError(f"Fail to get uitree, err: {org_echo}")
        path = echo[path_start:].strip()
        self.device.pull_file(path, tmp_tree_path, timeout=10 * 1000)
        if not os.path.isfile(tmp_tree_path):
            raise HypiumOperationFailError(f"Fail to pull uitree, err: {org_echo}")
        self.device.execute_shell_command("rm " + path, timeout=10 * 1000)
        return tmp_tree_path

    def _refresh(self, tmp_tree_path=None, config=None):
        """该函数用于方便refresh函数实现异常时支持重试获取控件树"""
        # 清空现有数据
        self.xml_tree = None
        self.tree = None
        self.tree_file = ""
        self._screenshot = None
        if config is None:
            config = UiTreeDumpConfig()
        tmp_tree_path = self._dump_uitest_layout(tmp_tree_path, config)
        self.load_file(tmp_tree_path)
        return self.tree

    def backup_layout(self, path):
        if os.path.exists(self.tree_file):
            try:
                shutil.copyfile(self.tree_file, path)
                self.driver.log_debug("backup err layout to %s" % path)
            except Exception as e:
                self.driver.log_info(f"Fail to backup layout, {repr(e)}")

    def set_tmp_dir(self, tmp_dir):
        """
        @func 设置查找控件时, 控件树临时保存目录
        """
        if os.path.isdir(tmp_dir):
            self.tmp_dir = tmp_dir
        else:
            raise ValueError(f"invalid dir [{tmp_dir}]")

    def dump_to_file(self, file_path, **kwargs) -> str:
        """
        @func dump控件树到指定文件路径
        @param file_path: 输出的layout文件保存路径
        @param kwargs: 可以通过kwargs的方式支持UiTreeDumpConfig中的配置项
        @return 返回文件路径
        """
        dir_name = os.path.dirname(file_path)
        if len(dir_name) != 0 and not os.path.exists(dir_name):
            os.makedirs(dir_name)
        config = UiTreeDumpConfig()
        config.__dict__.update(kwargs)
        self._refresh(file_path, config=config)
        return file_path

    def dump_to_dir(self, dir_path="", **kwargs) -> str:
        """
        @func dump控件树到指定目录
        @param dir_path: 目录名称
        @param kwargs: 可以通过kwargs的方式支持UiTreeDumpConfig中的配置项
        @return: 返回文件全路径, 文件名为layout_<timestamp>.json
        """
        file_name = "%s_layout_%s.json" % (utils.normalize_device_sn_to_filename(self.driver.device_sn),
                                           int(time.time() * 1000))
        file_path = os.path.join(dir_path, file_name)
        self.dump_to_file(file_path, **kwargs)
        return file_path

    def _get_tmp_path(self):
        """
        读取临时目录
        """
        report_path = self.driver._device.get_device_report_path()
        try:
            if isinstance(report_path, str) and os.path.isdir(report_path):
                full_path = os.path.join(report_path, "hypium_screenshot")
                os.makedirs(full_path, exist_ok=True)
                return full_path
        except Exception as e:
            self.driver.log_warning("Fail to get tmp screenshot in report path: %s" % repr(e))
        return utils.get_tmp_dir()

    @timer.timer
    def dump_page_info(self, dir_path="", screenshot=True, layout=True) -> Page:
        """
        @func dump控件树到指定目录
        @param dir_path: 文件保存的目录路径
        """
        if not os.path.exists(dir_path):
            dir_path = self._get_tmp_path()
        file_name = "%s_screenshot_%s.jpeg" % (
            utils.normalize_device_sn_to_filename(self.driver.device_sn),
            int(time.time() * 1000))
        file_path = os.path.join(dir_path, file_name)
        screenshot_path = ""
        layout_path = ""
        if screenshot:
            screenshot_path = self.driver.screenshot(file_path)
        if layout:
            layout_path = self.dump_to_dir(dir_path)
        return Page(screenshot_path, layout_path)

    def screenshot_to_dir(self, dir_path="") -> str:
        """
        @func dump控件树到指定目录
        @param dir_path: 目录名称
        @return: 返回文件全路径, 文件名为<device_sn>_screenshot_<timestamp>.json
        """
        file_name = "%s_screenshot_%s.jpeg" % (
            utils.normalize_device_sn_to_filename(self.driver.device_sn),
            int(time.time() * 1000))
        file_path = os.path.join(dir_path, file_name)
        self.driver.screenshot(file_path)
        return file_path

    def _generate_xml_tree(self, json_node):
        try:
            from hypium.utils import xml_builder
            self.xml_tree = xml_builder.build_xml_tree(json_node)
        except ImportError as e1:
            self.xml_tree = None
            raise ImportError(f"No lxml installed, please install lxml")
        except Exception as e:
            self.xml_tree = None
            traceback.print_exc()
            raise ValueError(f"Fail to load xml layout, {repr(e)}")

    def _generate_xml_tree_old(self, json_tree):
        try:
            xml_str = json_to_xml(json_tree)
            from lxml import etree
            tree = etree.fromstring(xml_str)
            self.xml_tree = tree
        except ImportError as e1:
            self.xml_tree = None
            raise ImportError(f"No lxml installed, please install lxml")
        except Exception as e:
            self.xml_tree = None
            traceback.print_exc()
            raise ValueError(f"Fail to load xml layout, {repr(e)}")

    def load_file(self, tree_file: str):
        self.tree_file = tree_file
        with open(self.tree_file, "r", encoding="utf-8", errors="ignore") as f:
            try:
                self.tree = json.load(f)
            except json.decoder.JSONDecodeError as e:
                f.seek(0)
                preview = f.read()
                self.driver.log_error(f"Fail to decode layout, invalid json str {e}")

    def _normalize_xpath(self, xpath):
        """
        部分xpath需要拼接用户输入的字符串, 因此采用FormatString类表示。
        该函数将str类型的xpath和FormatString类型的xpath统一为FormatString类型xpath
        """
        if isinstance(xpath, str):
            result = FormatString(xpath)
        elif isinstance(xpath, FormatString):
            result = xpath
        else:
            raise TypeError("Invalid xpath type: %s" % type(xpath))
        return result

    def _do_find_all_by_xpath(self, xpath):
        driver = self.driver
        if self.xml_tree is None:
            self._generate_xml_tree(self.tree)
        xpath = _convert_absolute_path(xpath)
        normalize_xpath = self._normalize_xpath(xpath)
        result = self.xml_tree.xpath(normalize_xpath.template, **normalize_xpath.variables)
        if len(result) > 0:
            matched_comps = []
            for i in result:
                matched_comps.append(XpathWidget(i, [], driver))
            return matched_comps
        else:
            return []

    def _do_find_by_xpath(self, xpath):
        driver = self.driver
        if self.xml_tree is None:
            self._generate_xml_tree(self.tree)
        xpath = _convert_absolute_path(xpath)
        normalize_xpath = self._normalize_xpath(xpath)
        result = self.xml_tree.xpath(normalize_xpath.template, **normalize_xpath.variables)
        if len(result) > 0:
            return XpathWidget(result[0], [], driver)
        else:
            return None

    @support_retry(lambda ret: len(ret) == 0)
    def find_all_by_xpath(self, xpath: str, refresh=True, timeout=0):
        """
        @func 支持xpath查找, 返回所有控件
        @param xpath: xpath路径
        @param refresh: 是否刷新本地UI控件树
        @return XpathWidget控件对象数组, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找文本为"打开"的控件
                 items = driver.UiTree.find_all_by_xpath("//Text[@text='5月20日']")
                 # 点击控件
                 driver.touch(items[0].center)
        """
        if refresh:
            self.refresh()
        return self._do_find_all_by_xpath(xpath)

    @support_retry(lambda ret: ret is None)
    def find_by_xpath(self, xpath, refresh=True, timeout=0):
        """
        @func 支持xpath查找控件, 返回第一个匹配的控件
        @param xpath: xpath路径
        @param refresh: 是否刷新本地UI控件树
        @return XpathWidget控件对象数组, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找文本为"备忘录"的控件
                 item = driver.UiTree.find_by_xpath("//Text[@text='备忘录']")
                 # 点击控件
                 driver.touch(item.center)
        """
        if refresh:
            self.refresh()
        return self._do_find_by_xpath(xpath)

    @support_retry(lambda ret: ret is None)
    def find_component_by_hierarchy(self, hierarchy_path: str, refresh=True, timeout: float = 0) -> Optional[UiWidget]:
        """
        @func 通过hierarchy路径查找控件
        @param hierarchy_path: 控件层级路径, 例如/0/1/0/2表示根节点下第1个子节点的第2个子节点的第1个子节点的第3个字节点
        @param refresh: 是否刷新控件树
        @return UiWidget控件对象, 保存控件位置和属性
        @example # 查找根节点下第1个子节点的第2个子节点的第1个子节点的第3个字节点
                 item = driver.UiTree.find_component_by_hierarchy("/0/1/0/2")
        """
        driver = self.driver
        if refresh:
            self.refresh()
        if type(hierarchy_path) != list:
            path = hierarchy_path.split("/")
        else:
            path = hierarchy_path
        if self.tree is None:
            return None
        node = self.tree
        for item in path:
            if type(item) != int and not item.isdigit():
                continue
            index = int(item)
            if "children" not in node.keys():
                return None
            children = node["children"]
            if len(children) <= index:
                return None
            node = children[index]
        return UiWidget(node, path.copy(), driver)

    def _do_find_all_component_with_relative_position(self, selector: BySelector, find_all=False,
                                                      matched_nodes: list = None):
        stop_item_count = 10000
        result = []
        if selector._before_selector:
            before_node = None
            # 取满足before条件的最后一个元素
            for index, node in enumerate(self._iterate_json_tree(self.tree)):
                if selector._before_selector.match(node):
                    stop_item_count = index
                    before_node = node
            if before_node is None:
                self.driver.log_warning("Fail to find before node")
                return result

        start_item_count = 0
        if selector._after_selector:
            after_node = None
            # 取满足after的第一个元素
            for index, node in enumerate(self._iterate_json_tree(self.tree)):
                if selector._after_selector.match(node):
                    start_item_count = index
                    after_node = node
                    break
            if after_node is None:
                self.driver.log_warning("Fail to find after node")
                return result
        # 查找目标控件
        if isinstance(matched_nodes, list):
            result = matched_nodes
        for index, node in enumerate(self._iterate_json_tree(self.tree)):
            if index <= start_item_count:
                continue
            if index >= stop_item_count:
                return result
            if selector.match(node):
                widget = UiWidget(node, [0], self.driver)
                if self._compare_widget_image_similarity(selector, widget):
                    result.append(widget)
                if not find_all:
                    break
        return result

    def _do_find_component(self, selector, node, hierarchy: list):
        driver = self.driver
        if selector is None or node is None:
            return None
        if selector.match(node):
            widget = UiWidget(node, hierarchy.copy(), driver)
            if self._compare_widget_image_similarity(selector, widget):
                return UiWidget(node, hierarchy.copy(), driver)

        if "children" in node.keys():
            i = 0
            for item in node["children"]:
                hierarchy.append(i)
                result = self._do_find_component(selector, item, hierarchy)
                hierarchy.pop()
                if result:
                    return result
                i += 1
            return None
        else:
            return None

    def _find_component(self, selector, node, hierarchy: list):
        if selector._xpath:
            return self._do_find_by_xpath(selector._xpath)
        elif selector._abspath:
            return self._do_find_component_by_path(selector._abspath)
        elif selector._before_selector or selector._after_selector:
            result = self._do_find_all_component_with_relative_position(selector, find_all=False)
            return result[0] if len(result) > 0 else None
        else:
            return self._do_find_component(selector, node, hierarchy)

    def _compare_widget_image_similarity(self, selector, widget: UiWidget):
        if selector._image is None:
            return True

        if self._screenshot is None:
            return False
        try:
            bounds = widget.bounds
            widget_image = self._screenshot[bounds.top: bounds.bottom, bounds.left: bounds.right]
            from hypium.utils.cv import image_similarity
            similarity = image_similarity.calculate_similarity(selector._image, widget_image)
            return similarity >= selector._image_similarity
        except Exception as e:
            basic_log.warning("Fail to get widget image %s" % repr(e))
            return False

    def _do_find_all_components(self, selector, node, hierarchy: list, matched_comps: list, only_count=False):
        count = 0
        driver = self.driver
        if selector is None or node is None:
            return count
        if selector.match(node):
            widget = UiWidget(node, hierarchy.copy(), driver)
            # 执行控件区域截图对比
            if self._compare_widget_image_similarity(selector, widget):
                if not only_count:
                    matched_comps.append(widget)
                count += 1
        if "children" in node.keys():
            i = 0
            for item in node["children"]:
                hierarchy.append(i)
                result = self._do_find_all_components(selector, item, hierarchy, matched_comps, only_count)
                hierarchy.pop()
                i += 1
                count += result
        return count

    def _find_all_components(self, selector, node, hierarchy: list, matched_comps: list, only_count=False):
        if selector._xpath:
            results = self._do_find_all_by_xpath(selector._xpath)
            matched_comps.extend(results)
            return len(results)
        elif selector._abspath:
            result = self._do_find_component_by_path(selector._abspath)
            if result:
                matched_comps.append(result)
            return len(matched_comps)
        elif selector._before_selector or selector._after_selector:
            result = self._do_find_all_component_with_relative_position(selector,
                                                                        find_all=True,
                                                                        matched_nodes=matched_comps)
            return len(result)
        else:
            return self._do_find_all_components(selector, node, hierarchy, matched_comps, only_count)

    @support_retry(lambda ret: len(ret) <= 0)
    def find_all_components(self, selector: Union[BySelector, By], refresh=True, timeout: float = 0) -> list:
        """
        @func 通过控件属性查找控件
        @param selector: 控件查找条件
        @param refresh: 是否刷新本地UI控件树
        @return UiWidget控件对象数组, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找文本为"打开"的控件
                 items = driver.UiTree.find_all_component(BySelector().text("打开"))
                 # 点击控件
                 driver.touch(item.center)
        """
        if type(selector) == By:
            selector = BySelector.from_by(selector)
        config = UiTreeDumpConfig()
        config.display_id = selector._display_id
        if refresh:
            self.refresh()
        hierarchy = []
        selector.reset_matcher()
        matched_comps = []
        self._find_all_components(selector, self.tree, hierarchy, matched_comps)
        return matched_comps

    @support_retry(lambda ret: ret == 0)
    def count_all_components(self, selector: Union[BySelector, By], refresh=True, timeout: float = 0) -> int:
        """
        @func 通过控件属性计算匹配的控件数量
        @param selector: 控件查找条件
        @param refresh: 是否刷新本地UI控件树
        @return 满足查找条件的控件数量
        @example # 统计当前页面文本为"打开"的控件的数量
                 number = driver.UiTree.count_all_components(BySelector().text("打开"))
        """
        if type(selector) == By:
            selector = BySelector.from_by(selector)
        config = UiTreeDumpConfig()
        config.display_id = selector._display_id
        if refresh:
            self.refresh()
        hierarchy = []
        selector.reset_matcher()
        matched_comps = []
        return self._find_all_components(selector, self.tree, hierarchy, matched_comps, only_count=True)

    @support_retry(lambda ret: ret is None)
    def find_component(self, selector: Union[BySelector, By], refresh=True, timeout: float = 0) -> Optional[UiWidget]:
        """
        @func 通过控件属性查找控件
        @param selector: 控件查找条件
        @param refresh: 是否刷新本地UI控件树
        @return UiWidget控件对象, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找文本为"打开"的控件
                 item = driver.UiTree.find_component(BySelector().text("打开"))
                 # 点击控件
                 driver.touch(item.center)
        """
        if type(selector) == By:
            selector = BySelector.from_by(selector)
        config = UiTreeDumpConfig()
        config.display_id = selector._display_id
        if refresh:
            self.refresh()
        hierarchy = []
        selector.reset_matcher()
        result = self._find_component(selector, self.tree, hierarchy)
        return result

    def _do_find_component_by_path(self, path: str):
        driver = self.driver
        path = path.split("/")
        if self.tree is None:
            return None
        node = self.tree
        for item in path:
            if len(item) == 0:
                continue
            result = re.match("([a-zA-Z_]+)(\[(\d+)\])?", item)
            if result is None:
                self.device.log.warning("invalid node in path: [%s]" % item)
                continue
            node_type, node_index_with_bracket, node_index = result.groups()
            if node_index is not None:
                node_index = int(node_index)
            else:
                node_index = 0
            if "children" not in node.keys():
                return None
            children = node["children"]
            match_index = 0
            match = False
            for cur_node in children:
                if cur_node["attributes"]["type"] == node_type:
                    if match_index == node_index:
                        node = cur_node
                        match = True
                        break
                    else:
                        match_index += 1
            if not match:
                return None
        return UiWidget(node, path.copy(), driver)

    @support_retry(lambda ret: ret is None)
    def find_component_by_path(self, path: str, refresh: bool = True, timeout: float = 0) -> Optional[UiWidget]:
        """
        @func 通过hierarchy路径查找控件
        @param path: 控件路径, 使用Testing的UiView查看的path, 如/root[2]/Column/Flex/Text[2]
        @param refresh: 是否刷新本地UI控件树
        @return UiWidget控件对象, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找根节点下第1个子节点的第2个子节点的第1个子节点的第3个字节点
                 item = driver.UiTree.find_component_by_path("/root[2]/Column/Flex/Text[2]")
                 # 点击控件
                 driver.touch(item.center)
        """
        if refresh:
            self.refresh()
        return self._do_find_component_by_path(path)

    @support_retry(lambda ret: ret is None)
    def find_component_by_relative_path(self, anchor: Union[BySelector, By], relative_path: str,
                                        refresh=True, timeout: float = 0) -> Optional[UiWidget]:
        """
        @func 通过相对路径查找控件
        @param anchor: 用于定位的锚点控件查找条件
        @param relative_path: 目标控件相对于锚点控件的路径, ..表示父节点, /1表示当前节点的第2个子节点(编号从0开始),
                              例如../../../3表示锚点控件的父节点的父节点的父节点的第4个子节点
        @param refresh: 是否刷新控件树, True表示先刷新再查找，False表示不刷新直接使用缓存的控件树查找
        @return UiWidget控件对象, 保存控件位置和属性
        @example: # 根据相对路径查找text为toast的控件的父控件下的第二个子控件(../1)(索引从0开始)
                  item = driver.UiTree.find_component_by_relative_path(BySelector().text("toast"), "../1")
                  # 打印控件的type属性
                  driver.log_info(item.type)
                  # 打印控件的id属性
                  driver.log_info(item.id)
                  # 打印控件的text属性
                  driver.log_info(item.text)
                  # 点击控件的中心点
                  driver.touch(item.center)
        """
        item = self.find_component(anchor, refresh=refresh)
        if item is None:
            return None
        target_path = item.hierarchy.copy()
        path = relative_path.split("/")
        for item in path:
            if item == "..":
                if len(target_path) < 1:
                    return None
                target_path.pop()
            elif item.isdigit():
                target_path.append(int(item))
            else:
                continue
        return self.find_component_by_hierarchy(target_path, refresh=False)

    @support_retry(lambda ret: len(ret) == 0)
    def find_all_components_by_relative_path(self, anchor: Union[BySelector, By], relative_path: str,
                                             refresh=True, timeout: float = 0) -> List[UiWidget]:
        """
        @func 查找所有的锚点控件对应的相对路径控件
              (注意某些不同的锚点控件在同样的相对路径下对应的控件可能相同，因此返回的结果可能有重复控件)
        @param anchor: 用于定位的锚点控件查找条件
        @param relative_path: 目标控件相对于锚点控件的路径, ..表示父节点, /1表示当前节点的第2个子节点(编号从0开始),
                              例如../../../3表示锚点控件的父节点的父节点的父节点的第4个子节点
        @param refresh: 是否刷新控件树, True表示先刷新再查找，False表示不刷新直接使用缓存的控件树查找
        @return UiWidget控件对象list, 保存控件位置和属性, 如果没有结果则返回空
        @example: # 根据相对路径查找所有text为toast的控件的父控件下的第二个子控件(../1)(索引从0开始)
                  items = driver.UiTree.find_all_components_by_relative_path(BySelector().text("toast"), "../1")
        """
        items = self.find_all_components(anchor, refresh=refresh)
        if len(items) == 0:
            return items
        result = []
        for item in items:
            target_path = item.hierarchy.copy()
            path = relative_path.split("/")
            for path_item in path:
                if path_item == "..":
                    if len(target_path) < 1:
                        break
                    target_path.pop()
                elif path_item.isdigit():
                    target_path.append(int(path_item))
                else:
                    continue
            current_target = self.find_component_by_hierarchy(target_path, refresh=False)
            if current_target is not None:
                result.append(current_target)
        return result

    def __str__(self):
        return "UiTree#%s" % id(self)

    def __repr__(self):
        return self.__str__()


class UiTreeComponentFinder(IComponentFinder):

    def __init__(self, driver: IAtomicDriver):
        self.driver = driver
        self._uitree = UiTree(driver)
        from hypium.uidriver.uitree.widget_finder import WidgetFinderManager
        self._ai_widget_finder_manager = WidgetFinderManager(self.driver.config)

    def is_selector_support(self, selector) -> bool:
        """返回是否支持指定的selector"""
        if isinstance(selector, BySelector):
            return True
        elif isinstance(selector, By):
            try:
                BySelector.from_by(selector)
                return True
            except Exception as e:
                basic_log.warning("selector not support: %s" % repr(e))
                return False
        else:
            return False

    def find_component(self, selector, timeout):
        if isinstance(selector, BySelector) and selector._target_description:
            description = selector._target_description
            return self._find_one_by_ai_widget_finder(description, timeout=timeout)
        return self._uitree.find_component(selector, timeout=timeout)

    def find_components(self, selector, timeout):
        if isinstance(selector, BySelector) and selector._target_description:
            description = selector._target_description
            return self._find_all_by_ai_widget_finder(description, timeout=timeout)

        return self._uitree.find_all_components(selector, timeout=timeout)

    @support_retry(lambda x: x is None)
    def _find_one_by_ai_widget_finder(self, description, timeout=0):
        page = self._uitree.dump_page_info()
        result = self._ai_widget_finder_manager.find_one(page, description)
        if result is None:
            return result
        widget = UiWidget({}, [], self.driver, bounds=result.bounds)
        return widget

    @support_retry(lambda x: len(x) == 0)
    def _find_all_by_ai_widget_finder(self, description, timeout=0):
        page = self._uitree.dump_page_info()
        result = self._ai_widget_finder_manager.find_all(page, description)
        result = list(map(lambda x: UiWidget({}, [], self.driver, bounds=x.bounds), result))
        return result

    def _convert_to_component(self, item):
        left, top, right, bottom = item
        return UiWidget({"attributes": {"bounds": "[%s,%s][%s,%s]" % (left, top, right, bottom)}}, "",
                        self.driver)
