import threading
from .dvt_logger import deveco_log
from devicetest.core.variables import DeccVariable
from .utils import ThreadLocalVar
import os


class TaskEventFactory:

    @staticmethod
    def create_task_start(task_name, total_case):
        return {
            "type": "TaskStart",
            "name": task_name,
            "total_case": total_case
        }

    @staticmethod
    def create_task_end(task_name, passed, failed, error=None):
        error = "" if error is None else error
        return {
            "type": "TaskEnd",
            "name": task_name,
            "passed": passed,
            "failed": failed,
            "error": error
        }

    @staticmethod
    def create_case_start(case_name, case_id):
        return {
            "type": "CaseStart",
            "name": case_name,
            "id": case_id
        }

    @staticmethod
    def create_case_end(case_name, case_id, result, error=None):
        error = "" if error is None else error
        return {
            "type": "CaseEnd",
            "name": case_name,
            "id": case_id,
            "result": result,
            "error": error
        }

    @staticmethod
    def create_step_start(step_name, step_id, desc):
        return {
            "type": "StepStart",
            "name": step_name,
            "id": step_id,
            "desc": desc
        }

    @staticmethod
    def create_step_end(step_name, step_id, result, error=None, screenshot=None):
        error = "" if error is None else error
        return {
            "type": "StepEnd",
            "name": step_name,
            "id": step_id,
            "result": result,
            "error": error,
            "screenshot": screenshot
        }

    @staticmethod
    def create_update_metric(name, value, unit):
        return {
            "type": "Metric",
            "name": name,
            "value": value,
            "unit": unit
        }


class TaskEventListener:

    def on_task_start(self, event_info: dict):
        pass

    def on_task_end(self, event_info: dict):
        pass

    def on_case_start(self, event_info: dict):
        pass

    def on_case_end(self, event_info: dict):
        pass

    def on_step_start(self, event_info: dict):
        pass

    def on_step_end(self, event_info: dict):
        pass

    def on_update_metric(self, event_info: dict):
        pass


class _TaskManager:

    def __init__(self):
        self.listeners = dict()
        # 事件通知模式, 0表示使用应用拨测1.0的日志格式, 1表示使用新模式
        self.mode = 0
        # 任务事件通知是否已激活
        self._enable = False
        # 其他任务属性
        self.total_cases = 0
        self.current_case_index = 0

    def enable(self):
        try:
            from xdevice import Task
            Task.life_stage_listener = self.on_event
            self._enable = True
        except Exception as e:
            deveco_log.warning("Fail to enable TaskEventManager")

    def register_event_listener(self, name, listener: TaskEventListener):
        self.listeners[name] = listener

    def unregister_event_listener(self, name):
        self.listeners.pop(name)

    def on_event(self, event_info: dict):
        if type(event_info) is not dict or "type" not in event_info.keys():
            deveco_log.warning("invalid event: %s" % str(event_info))
            return
        self.notify_listeners(event_info)

    def notify_listeners(self, event_info):
        event_type = event_info.get("type")
        if event_type == "TaskStart":
            self.total_cases = event_info.get("total_cases", 0)
            for listener in self.listeners.values():
                try:
                    listener.on_task_start(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        elif event_type == "TaskEnd":
            for listener in self.listeners.values():
                try:
                    listener.on_task_end(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        elif event_type == "CaseStart":
            self.current_case_index += 1
            event_info["id"] = self.current_case_index
            for listener in self.listeners.values():
                try:
                    listener.on_case_start(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        elif event_type == "CaseEnd":
            event_info["id"] = self.current_case_index
            for listener in self.listeners.values():
                try:
                    listener.on_case_end(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        elif event_type == "StepStart":
            for listener in self.listeners.values():
                try:
                    listener.on_step_start(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        elif event_type == "StepEnd":
            for listener in self.listeners.values():
                try:
                    listener.on_step_end(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        elif event_type == "Metric":
            for listener in self.listeners.values():
                try:
                    listener.on_update_metric(event_info)
                except Exception as e:
                    deveco_log.warning("Fail to call listener: %s", str(e))
        else:
            deveco_log.warning("invalid event type: %s" % str(event_type))


TaskManager = _TaskManager()






