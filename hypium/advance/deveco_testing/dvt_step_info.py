import json
import sys
import os
from xdevice import Task
from .task_event_manager import TaskEventListener, TaskManager, TaskEventFactory
from .step import *
from .metric import DevecoTesting_set_metric, DevecoTesting_get_metric
from .dvt_logger import deveco_log, DvtLogger


class TaskEventListenerForTesting(TaskEventListener):

    def on_case_start(self, event_info: dict):
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)

    def on_case_end(self, event_info: dict):
        case_end_callback(event_info.get("error_msg", ""))
        result = event_info.get("case_result", "failed")
        result = "passed" if "pass" in result.lower() else "failed"
        event_info = TaskEventFactory.create_case_end(
            event_info.get("name", "unknown_name"),
            event_info.get("id", -1),
            result,
            event_info.get("error_msg", "")
        )
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)

    def on_task_start(self, event_info: dict):
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)

    def on_task_end(self, event_info: dict):
        # passed: 0, failed: 1, blocked: 0, ignored: 0, unavailable: 0
        passed_cases = event_info.get("passed", 0)
        failed_cases = 0
        for item in ("failures", "blocked", "unavailable"):
            failed_cases += event_info.get(item, 0)
        event_info_key_1 = "exception"
        event_info_key_2 = "error"
        error = None
        if event_info_key_1 in event_info.keys():
            error = event_info.get(event_info_key_1)
        elif event_info_key_2 in event_info.keys():
            error = event_info.get(event_info_key_2)
        event_info = TaskEventFactory.create_task_end(
            event_info.get("name", "unknown_name"),
            passed_cases,
            failed_cases,
            error
        )
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)

    def on_step_end(self, event_info: dict):
        result = event_info.get("result", "failed")
        result = "passed" if "pass" in result.lower() else "failed"
        if event_info.get("error", None) is None:
            event_info["error"] = ""
        event_info = TaskEventFactory.create_step_end(
            event_info.get("name", "unknown"),
            event_info.get("id", -1),
            result,
            event_info.get("error", ""),
            event_info.get("screenshot", [])
        )
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)

    def on_step_start(self, event_info: dict):
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)

    def on_update_metric(self, event_info: dict):
        msg = json.dumps(event_info, ensure_ascii=False)
        deveco_log.info(msg)


def register_task_event_listener():
    TaskManager.enable()
    TaskManager.mode = 1
    work_dir = os.path.join(os.getcwd())
    log_path = os.path.join(work_dir, 'process', 'process_log.txt')
    DvtLogger.log_path = log_path
    # set output charset to utf-8
    sys.stdout.reconfigure(encoding='utf-8', errors="ignored")
    TaskManager.register_event_listener("basic", TaskEventListenerForTesting())
