import dataclasses
import logging
from typing import Optional
from hypium.utils import utils
import os
from datetime import datetime
import time

try:
    from devicetest.record_actions.record_action import RecordAction
except ImportError:
    from hypium.utils.implement_utils import GenericObject as RecordAction

logger = logging.getLogger("Tracker")


def track_adaptive_event(event_id, result):
    try:
        RecordAction.track_adaptive_event(event_id=event_id, result=result)
    except Exception as e:
        logger.debug("Fail to track adaptive event, err: [%s]" % repr(e))


@dataclasses.dataclass
class EventItem:
    id: str
    name: str


class TrackerEvent:
    APP_INFO = EventItem("907001004", "AppInfo")
    SDK_MODE = EventItem("907001003", "SDKMode")


class UpLoadTimeManager:
    """
    SDK打点上报管理
    """

    def __init__(self):
        self.tracker_flag_file = os.path.join(utils.get_system_temp_dir(), "tracker_flag.txt")
        self.last_upload_time: Optional[datetime] = None
        self.upload_interval = 3600
        self._disable_block = False

    def load_upload_time(self):
        self.last_upload_time = self.get_timestamp_in_file(self.tracker_flag_file)

    def need_upload(self, interval=None):
        if self.last_upload_time is None:
            self.load_upload_time()
        if not interval:
            interval = self.upload_interval
        current = datetime.now()
        diff = current - self.last_upload_time
        if diff.total_seconds() >= interval:
            self.write_current_timestamp(self.tracker_flag_file)
            self.last_upload_time = current
            return True
        elif diff.total_seconds() < 0:
            self.write_current_timestamp(self.tracker_flag_file)
            self.last_upload_time = current
            return True
        else:
            return False

    @staticmethod
    def write_current_timestamp(file_path: str, use_iso_format: bool = True) -> None:
        """
        将当前系统时间以指定格式写入文件

        参数:
        file_path (str): 要写入的文件路径
        use_iso_format (bool): 是否使用ISO格式，默认为True；
                               若为False，则使用Unix时间戳格式

        返回:
        None

        异常:
        PermissionError: 如果没有权限写入文件
        OSError: 如果写入文件时发生其他错误
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            current_time = datetime.now()
            if use_iso_format:
                content = current_time.isoformat()
            else:
                content = str(current_time.timestamp())
            with open(file_path, 'w') as file:
                file.write(content)
        except Exception as e:
            logger.warning("Fail to write tmp file: %s" % repr(e))

    def get_timestamp_in_file(self, file_path: str):
        """
        计算指定文件中保存的时间与当前系统时间的秒数差值

        参数:
        file_path (str): 包含时间戳的文件路径

        返回:
        float: 时间差值（秒）

        异常:
        FileNotFoundError: 如果指定的文件不存在
        ValueError: 如果文件内容无法转换为有效的datetime对象
        """
        saved_time = datetime.fromtimestamp(time.time() - self.upload_interval)
        if not os.path.exists(file_path):
            return saved_time

        try:
            with open(file_path, 'r') as file:
                content = file.read().strip()
                # 尝试解析ISO格式的日期时间字符串
                saved_time = datetime.fromisoformat(content)
        except ValueError:
            # 尝试解析时间戳格式
            try:
                timestamp = float(content)
                saved_time = datetime.fromtimestamp(timestamp)
            except ValueError:
                return saved_time

        return saved_time


class Tracker:
    upload_manager = UpLoadTimeManager()
    _is_sdk_mode = None

    @staticmethod
    def event(*args, **kwargs):
        try:
            from xdevice import Tracker as XDeviceTracker
            XDeviceTracker.event(*args, **kwargs)
        except Exception:
            logger.debug("tracker failed")
        Tracker.upload()

    @staticmethod
    def is_sdk_mode():
        if Tracker._is_sdk_mode is not None:
            return Tracker._is_sdk_mode
        try:
            from xdevice import is_env_pool_run_mode
            if is_env_pool_run_mode():
                Tracker._is_sdk_mode = True
            else:
                Tracker._is_sdk_mode = False
        except Exception:
            logger.debug("tracker failed")
        return Tracker._is_sdk_mode

    @staticmethod
    def event_sdk_mode(*args, **kwargs):
        if not Tracker.is_sdk_mode():
            return
        try:
            from xdevice import Tracker as XDeviceTracker
            XDeviceTracker.event(*args, **kwargs)
        except Exception:
            logger.debug("tracker failed")
        Tracker.upload()

    @staticmethod
    def upload():
        need_upload = False
        try:
            if not Tracker.is_sdk_mode():
                return
            need_upload = Tracker.upload_manager.need_upload()
        except Exception as e:
            logger.debug("Fail to get upload timestamp: %s" % repr(e))

        if not need_upload:
            return

        try:
            from xdevice import Tracker as XDeviceTracker
            xdevice_upload_interval = "immediately" if Tracker.upload_manager.upload_interval == 0 else "24H"
            XDeviceTracker.upload(before=xdevice_upload_interval)
        except Exception:
            logger.debug("tracker upload failed")
