import traceback
from typing import Iterable
from abc import abstractmethod, ABC
from hypium.utils.logger import basic_log
from hypium.uidriver.interface.atomic_driver import IComponentFinder


class MultiModeComponentFinder(IComponentFinder):
    """支持多种控件查找模式, 根据selector尝试合适的查询方式"""
    @property
    @abstractmethod
    def sorted_finders(self) -> Iterable[IComponentFinder]:
        pass

    def is_selector_support(self, selector) -> bool:
        for finder in self.sorted_finders:
            if finder.is_selector_support(selector):
                return True
        return False

    def find_component(self, selector, timeout):
        last_err = None
        for finder in self.sorted_finders:
            try:
                if not finder.is_selector_support(selector):
                    continue
                return finder.find_component(selector, timeout)
            except Exception as e:
                basic_log.warning("Fail to find component with %s, error: %s" % (finder, repr(e)))
                basic_log.error(traceback.format_exc())
                last_err = e
                continue
        if last_err:
            raise last_err
        return None

    def find_components(self, selector, timeout):
        last_err = None
        for finder in self.sorted_finders:
            try:
                if not finder.is_selector_support(selector):
                    continue
                return finder.find_components(selector, timeout)
            except Exception as e:
                basic_log.warning("Fail to find component with %s, error: %s" % (finder, repr(e)))
                last_err = e
                continue
        if last_err:
            raise last_err
        return []
