"""
弹窗处理模块
"""
import datetime
import json
import os
import subprocess
import sys
import time
import traceback
import socket
from xdevice import Variables
from hypium.uidriver.common import report_helper
from hypium.model.driver_config import DriverConfig

try:
    from hypium.advance.perf.analysis_time import AnalysisTools, get_time_cost
    from hypium.advance.perf.log import LOG
except Exception:
    print("No perf plugin loaded, using mock symbol")


    class MockTools:
        POPUP_WINDOWS_TIMES = 0
        POPUP_WINDOWS_TIME = 0


    AnalysisTools = MockTools()


    def get_time_cost(start_time):
        return time.time() - start_time

from hypium.action.device.uidriver import UiDriver
from hypium.utils.logger import basic_log
from hypium.utils.utils import Timer
from hypium.utils import utils, module_loader
from hypium.uidriver import ArkUiDriver
import re


def handle_pop_up_window(driver, max_try_times=2, timeout: float = 30):
    AnalysisTools.POPUP_WINDOWS_TIMES += 1
    start_time = time.time()
    timer = Timer()
    timer.start()
    if hasattr(driver, "PopWindowService"):
        driver.PopWindowService.handle_pop_window(max_try_times=max_try_times, timeout=timeout)
    else:
        driver.log_warning("Driver is not compatible, pop window dismiss not working")
    driver.log_info("pop window dismiss used %f s" % (timer.get_elapse()))
    AnalysisTools.POPUP_WINDOWS_TIME += get_time_cost(start_time)


def run_with_pop_up_window_handler(func):
    """操作失败后进行弹窗消除，然后重试"""

    def wrapper(*args, **kwargs):
        try_times = 2
        driver = None
        # 读取driver参数
        if len(args) == 1:
            driver = args[0]
        elif len(args) >= 2:
            driver = args[0] if type(args[0]) is ArkUiDriver else args[1]
        if type(driver) != ArkUiDriver:
            basic_log.error("No driver, can't run pop up window handler")
            return func(*args, **kwargs)
        for _ in range(try_times):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                basic_log.error("operation failed, %s %s" % (e.__class__.__name__, str(e)))
                handle_pop_up_window(driver)
        return None

    return wrapper


class PopWindowService:
    instances_list = set()

    def __init__(self, driver: UiDriver):
        self.process = None
        self.log_file_path = ""
        self.log_path = ""
        self.driver = driver
        self._startup_timeout = 30
        self._max_retry_times = 3
        self.pop_window_handler = None
        self._load_pop_window_rules()

    def _get_pop_window_rules_path(self):
        project_dir = Variables.exec_dir
        if isinstance(project_dir, str):
            device_config_path = os.path.join(Variables.exec_dir, "config", "pop_window_rules.py")
            if os.path.isfile(device_config_path):
                return device_config_path
        return ""

    def _check_rules(self, rules):
        if not isinstance(rules, list):
            raise ValueError("Invalid pop window rules")
        invalid_items = []
        for item in rules:
            from hypium.uidriver.uitree import BySelector
            is_valid_item = isinstance(item, dict) \
                            and "selectors" in item \
                            and "target_index" in item \
                            and isinstance(item["target_index"], int) \
                            and len(item["selectors"]) > 0 \
                            and isinstance(item["selectors"][0], BySelector)
            if not is_valid_item:
                invalid_items.append(item)

        if len(invalid_items) > 0:
            raise ValueError("Invalid pop window rules: " % invalid_items)

    def _load_pop_window_rules(self):
        from hypium.advance.pop_window_rules import pop_window_rules
        self.pop_window_data = pop_window_rules

        extra_pop_window_rules_file_path = self._get_pop_window_rules_path()
        if os.path.isfile(extra_pop_window_rules_file_path):
            try:
                extra_pop_window_rules_module = module_loader.load_module(extra_pop_window_rules_file_path)
                extra_pop_window_rules = getattr(extra_pop_window_rules_module, "pop_window_rules")
                self._check_rules(extra_pop_window_rules)
                self.pop_window_data = extra_pop_window_rules + self.pop_window_data
            except Exception as e:
                self.driver.log_warning("Fail to load pop window rules: [%s], err [%s]" %
                                        (extra_pop_window_rules_file_path, repr(e)))

    def enable_auto_dismiss(self, log_path=None, max_retry_times=3):
        """
        @func: 开启自动消除弹窗, 注意需要首先启动弹窗服务才能生效
        @param: log_path: 启动弹窗消除服务时, 日志保存路径, 如果服务未启动必须设置路径, 服务已经启动则设置不生效
        """
        self.driver.config.pop_window_dismiss = DriverConfig.PopWindowHandlerConfig.ENABLE
        self._max_retry_times = max_retry_times

    def disable_auto_dismiss(self, stop_service=False):
        """
        @func: 关闭自动消除弹窗, 注意需要首先启动弹窗服务才能生效
        @param: log_path: 启动弹窗消除服务时, 日志保存路径, 如果服务未启动必须设置路径, 服务已经启动则设置不生效
        """
        self.driver.config.pop_window_dismiss = DriverConfig.PopWindowHandlerConfig.DISABLE

    def add_layout_pop_window_handle_rule(self, rule: dict):
        """新增一个layout弹窗消除规则"""
        self.pop_window_data.append(rule)

    def handle_pop_window_by_layout(self):
        start = time.time()
        try:
            self.driver.UiTree.refresh()
            for pop_window_item in self.pop_window_data:
                results = []
                pop_window_selector, target_index = (pop_window_item.get("selectors", []),
                                                     pop_window_item.get("target_index", 0))
                for selector in pop_window_selector:
                    result = self.driver.UiTree.find_component(selector, refresh=False, timeout=0, PRINT_LOG=False)
                    if result is None:
                        results = []
                        break
                    results.append(result)
                if results:
                    target_index_normalized = target_index if target_index >= 0 else 0
                    self.driver.log.info(
                        "detect pop-window by layout, target widget %s" % pop_window_selector[target_index_normalized])
                    report_helper.log_screenshot(self.driver, message="detect pop up window")
                    if target_index >= 0:
                        self.driver.click(results[target_index].center)
                    else:
                        # target_index < 0表示通过返回键消除弹窗
                        self.driver.press_back()
                    return True
            self.driver.log_info("no pop-window found in layout")
            return False
        except Exception as e:
            self.driver.log_info("layout pop window detector failed: %s" % repr(e))
            return False
        finally:
            self.driver.log_info("layout pop-window detection used: %.2f s" % (time.time() - start))

    def handle_pop_window(self, max_try_times=None, timeout: float = 15):
        driver = self.driver
        AnalysisTools.POPUP_WINDOWS_TIMES += 1
        start_time = time.time()
        timer = Timer()
        timer.start()
        pop_window_dismissed = False
        if max_try_times is None:
            max_try_times = self._max_retry_times
        for _ in range(max_try_times):
            has_pop_up_window = self.handle_pop_window_by_layout()
            if not has_pop_up_window:
                break
            pop_window_dismissed = True
            time.sleep(2)
        driver.log_info("pop window dismiss time: %f s" % (timer.get_elapse()))
        AnalysisTools.POPUP_WINDOWS_TIME += get_time_cost(start_time)
        return pop_window_dismissed
