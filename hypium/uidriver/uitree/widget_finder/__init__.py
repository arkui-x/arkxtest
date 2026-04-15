import inspect
import re
from abc import abstractmethod, ABC
from typing import List
from hypium.model.basic_data_type import Rect
from hypium.uidriver.uitree.page import Page
from hypium.uidriver.uitree.page import WidgetInfo
from hypium.utils.logger import basic_log


class WidgetFinder(ABC):
    """
    指定语义类型控件查找器
    """

    @property
    @abstractmethod
    def category(self):
        """
        返回支持查找的控件类别
        """
        pass

    @abstractmethod
    def is_support(self, description: str) -> bool:
        return description == self.category

    @abstractmethod
    def find_one(self, page: Page, description: str = "") -> WidgetInfo:
        targets = self.find_all(page)
        if not targets:
            return None
        return targets[0]

    @abstractmethod
    def find_all(self, page: Page, description: str = "") -> List[WidgetInfo]:
        """
        返回所有匹配的控件
        """
        pass


class WidgetFinderManager(WidgetFinder):
    """
    根据用户定义创建控件查找器
    """

    @property
    def category(self):
        return "general_widget_finder"

    def is_support(self, description: str) -> bool:
        return True

    def __init__(self, config):
        self.config = config
        self.widget_finders: List[WidgetFinder] = []
        self._load_ai_widget_finder()

    def _load_ai_widget_finder(self):
        try:
            from .ai_widget_finder import AiWidgetFinder
            self.widget_finders.append(AiWidgetFinder())
        except ModuleNotFoundError as e:
            if "cv2" in e.msg:
                basic_log.error(
                    "Fail to load ai widget finder, no opencv-python, please install with pip install opencv-python")
        except Exception as e:
            basic_log.error("Fail to load ai widget finder: %s" % repr(e))

    def iter_widget_finder(self, description: str):
        from .ai_widget_finder import AiWidgetFinder
        for finder in self.widget_finders:
            if finder.is_support(description):
                yield finder

    def _convert_result_to_widget_info(self, result):
        if not result:
            widget_info = None
        else:
            left, top, right, bottom = result
            widget_info = WidgetInfo(Rect(left, right, top, bottom))
        return widget_info

    def find_one(self, page: Page, description: str) -> WidgetInfo:
        from .ai_widget_finder import AiWidgetFinder
        for finder in self.iter_widget_finder(description):
            sig = inspect.signature(finder.find_one)
            if "description" not in sig.parameters:
                result = finder.find_one(page)
            else:
                result = finder.find_one(page, description)

            # 返回值转换
            if not isinstance(finder, AiWidgetFinder):
                result = self._convert_result_to_widget_info(result)
            if result is not None:
                return result
        return None

    def find_all(self, page: Page, description: str) -> List[WidgetInfo]:
        result = []
        from .ai_widget_finder import AiWidgetFinder
        for finder in self.iter_widget_finder(description):
            sig = inspect.signature(finder.find_all)
            if "description" not in sig.parameters:
                result = finder.find_all(page)
            else:
                result = finder.find_all(page, description)

            if not isinstance(finder, AiWidgetFinder):
                result = list(map(self._convert_result_to_widget_info, result))

            if len(result) != 0:
                return result
        return result
