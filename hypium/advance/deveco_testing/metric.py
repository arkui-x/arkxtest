import os
import json
from typing import Any
from devicetest.core.variables import DeccVariable
from .dvt_logger import DvtLogger, deveco_log
from .utils import ThreadLocalVar, GlobalVar
from .task_event_manager import TaskManager, TaskEventFactory


def standardize_metric(name, value, unit):
    """对用户传入的指标值参数进行标准化处理"""
    if not isinstance(name, str):
        name = str(name)
    if len(name) > 20:
        name = name[0:20]
    if (not isinstance(value, int)) and (not isinstance(value, float)):
        value = str(value).strip()
        if value.isdigit():
            value = int(value)
        elif '.' in value and len(value.split('.')) == 2:
            a, b = value.split('.')
            if a.isdigit() and b.isdigit():
                value = float(value)
            else:
                value = None
        else:
            value = None
    if not isinstance(unit, str):
        unit = str(unit)
    if len(unit) > 5:
        unit = unit[0:5]
    return name, value, unit


def _create_metric_logger(log_dir=None):
    """适配拨测服务1.0版本日志"""
    if log_dir is None:
        log_dir = DvtLogger.log_path
        if os.path.isfile(log_dir):
            log_dir = os.path.dirname(DvtLogger.log_path)
    testcase_metric_path = os.path.join(log_dir, "testcase.metric")
    return DvtLogger.get_logger("metric", testcase_metric_path)


class DevEcoTestingMetric:

    def __init__(self, case_id=None, step_id=None):
        self.data = {}
        self.case_id = case_id
        self.step_id = step_id
        self.metric_logger = None

    def set(self, name: str, value: Any, unit: str = "", step=None):
        """上报/更新一个指标"""
        if hasattr(step, "id"):
            step_id = step.id
        else:
            step_id = self.step_id
        name, value, unit = standardize_metric(name, value, unit)
        if name in self.data.keys():
            metric_item = self.data[name]
        else:
            metric_item = {"case_id": self.case_id, "step_id": step_id}
        metric_item["name"] = name
        metric_item["value"] = value
        metric_item["unit"] = unit
        self.data[name] = metric_item
        if TaskManager.mode == 0:
            # 兼容应用拨测1.0
            if self.metric_logger is None:
                self.metric_logger = _create_metric_logger()
            self.metric_logger.info(metric_item)
            deveco_log.info("metric: %s: %s %s" % (name, value, unit))
        TaskManager.on_event(TaskEventFactory.create_update_metric(name, value, unit))

    def get(self, name: str) -> dict:
        """返回单个指标"""
        if name in self.data.keys():
            return self.data[name]
        else:
            return None

    def get_all(self) -> list:
        """返回指标列表"""
        return list(self.data.values())


def DevecoTesting_set_metric(name: str, value: float, unit: str = ""):
    """
    @func 上报一个指标
    @param name: 指标名称
    @param value: 指标值
    @param unit: 指标单位
    @example: # 上报温度, 值为30, 单位为摄氏度
              DevecoTesting_set_metric("temperature", 30, "℃" )
    """
    case_id = "unknown"
    if DeccVariable.cur_case() is not None:
        testcase = DeccVariable.cur_case().testcase
        case_id = testcase.__class__.__name__

    if ThreadLocalVar.current_metrics is None or \
            ThreadLocalVar.current_metrics.case_id is not case_id:
        ThreadLocalVar.current_metrics = DevEcoTestingMetric(case_id)
    ThreadLocalVar.current_metrics.set(name, value, unit)


def DevecoTesting_get_metric(name: str) -> dict:
    """
    @func 读取已上报的指标
    @param name: 指标名称
    @return: 代表指标的dict对象, 例如{"name": "metric_name", "value" : 10, "unit" : "xxx"}
    @example: metric = DevecoTesting_get_metric("metric_name")
    """
    if ThreadLocalVar.current_metrics is None:
        return None
    else:
        return ThreadLocalVar.current_metrics.get(name)
