# /usr/bin/env python
"""
hypium aw实现中使用的一些通用操作
"""
import json
import math
import os.path
import re
import signal
import subprocess
import time
import platform
from typing import Union, List
import hashlib
from hypium.utils.logger import basic_log

try:
    import cv2
    import numpy as np
except ImportError:
    basic_log.warning("cv2 is not available, please install opencv-python to use cv operation")

from datetime import datetime
from hypium.exception import HypiumParamError
from hypium.model.basic_data_type import Point, Rect
from hypium.utils.typevar import T

hypium_temp_file_dir = "tmp_hypium"


def cv_imread(file_path):
    cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), -1)
    return cv_img


def cv_imwrite(img, filepath, quality=80):
    params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    cv2.imencode('.jpeg', img, params=params)[1].tofile(filepath)


def compress_image(img_path: str, ratio: float = 0.5, quality=80):
    """压缩图像分辨率"""
    pic = cv_imread(img_path)
    height, width, deep = pic.shape
    width, height = (width * ratio, height * ratio)
    pic = cv2.resize(pic, (int(width), int(height)))
    cv_imwrite(pic, img_path, quality)


def limit_value_range(value: int, lower: int, upper: int) -> int:
    """
    @func value属于[lower, upper]区间时，返回value，
          value不属于[lower, upper]区间时，按照其大小返回lower或者upper
    """
    if value < lower:
        value = lower
    elif value > upper:
        value = upper
    return value


def compare_text(text: str, expect_text: str, fuzzy: str = None) -> bool:
    """支持多种匹配方式的文本匹配"""
    if fuzzy is None or fuzzy.startswith("equal"):
        result = (expect_text == text)
    elif fuzzy == "starts_with":
        result = text.startswith(expect_text)
    elif fuzzy == "ends_with":
        result = text.endswith(expect_text)
    elif fuzzy == "contains":
        result = expect_text in text
    elif fuzzy == "regexp":
        result = re.search(expect_text, text)
        result = False if result is None else True
    else:
        raise HypiumParamError("fuzzy", msg="expected [equal, starts_with, ends_with, contains], get [%s]" % fuzzy)
    return result


class TextMatcher:
    """
    字符串比较对象，传入字符串和比较方法，后续可以通过==或者!=来同字符串进行比较，
    例如TextMatch("like", TextMatcher.START_WITH) == "like_you"返回true
    """
    START_WITH = "start_with"
    END_WITH = "end_with"
    IN = "in"
    REGEXP = "regexp"

    def __init__(self, text: str, match_type: str):
        self.text = text
        if match_type == TextMatcher.START_WITH:
            self.matcher = self.match_start_with
        elif match_type == TextMatcher.END_WITH:
            self.matcher = self.match_end_with
        elif match_type == TextMatcher.IN:
            self.matcher = self.match_in
        elif match_type == TextMatcher.REGEXP:
            self.matcher = self.match_regexp
        else:
            raise RuntimeError("Not support match type: %s" % (match_type))

    @staticmethod
    def contain(text: str) -> 'TextMatcher':
        return TextMatcher(text, TextMatcher.IN)

    @staticmethod
    def start_with(text: str) -> 'TextMatcher':
        return TextMatcher(text, TextMatcher.START_WITH)

    @staticmethod
    def end_with(text: str) -> 'TextMatcher':
        return TextMatcher(text, TextMatcher.END_WITH)

    @staticmethod
    def regexp(text: str) -> 'TextMatcher':
        return TextMatcher(text, TextMatcher.REGEXP)

    def match(self, real_value):
        return self.matcher(real_value)

    def match_start_with(self, real_value: str):
        return real_value.startswith(self.text)

    def match_end_with(self, real_value: str):
        return real_value.endswith(self.text)

    def match_in(self, real_value: str):
        return self.text in real_value

    def match_regexp(self, real_value: str):
        if re.match(self.text, real_value) is not None:
            return True
        else:
            return False

    def __eq__(self, real_value):
        return self.matcher(real_value)

    def __ne__(self, real_value):
        return not self.matcher(real_value)


class Timer():
    '''
    计时器，用于统计操作的耗时
    '''

    def __init__(self):
        self.start()

    def start(self):
        '''
        启动计时器，记录当前时间
        '''
        self.start_time = time.time()

    def get_elapse(self, restart=True) -> float:
        '''
        获取计时开始到当前的经过的时间
        @param restart: 是否重新开始计时
        @return: 计时开始到当前的经过的时间
        '''
        if restart:
            return self.get_elapse_restart()
        else:
            return time.time() - self.start_time

    def get_elapse_restart(self) -> float:
        '''
        获取计时开始到当前的经过的时间, 并重新开始计时
        '''
        cur_time = time.time()
        elapse = cur_time - self.start_time
        self.start_time = cur_time
        return elapse


def is_cmd_success(echo: str) -> bool:
    """
    @func 检查shell命令执行是否成功，通过检查回显内容中是否存在负面词汇, 例如fail, error等
          来实现
    @param echo:
    @return:
    """
    if type(echo) != str:
        return False
    # 没有输出内容一般表示执行成功
    if len(echo) == 0:
        return True
    echo = echo.lower()
    negative_words = ["fail", "invalid", "error", "denied", "exception", "unknown"]
    for item in negative_words:
        if item in echo:
            return False
    return True


def parse_alpha_version(version_segment):
    result = re.search("([0-9]+)([ab])?([0-9]+)?", version_segment)
    if result is None:
        raise RuntimeError("Invalid version number segment, %s" % (version_segment))
    return result.groups()


def compare_number(a, b):
    result = int(a) - int(b)
    if result != 0:
        return -1 if result < 0 else 1
    return result


def compare_version(version_a, version_b):
    version_a = version_a.split('.')
    version_b = version_b.split('.')
    min_version_len = min(len(version_a), len(version_b))
    for i in range(min_version_len - 1):
        try:
            result = int(version_a[i]) - int(version_b[i])
            if result != 0:
                return -1 if result < 0 else 1
        except Exception:
            raise RuntimeError("Invalid version number, can't compare %s %s" % (version_a, version_b))
    last_version_num_a = version_a[min_version_len - 1]
    last_version_num_b = version_b[min_version_len - 1]
    result_a = parse_alpha_version(last_version_num_a)
    result_b = parse_alpha_version(last_version_num_b)
    result = 0
    for a, b in zip(result_a, result_b):
        if a is None or b is None:
            if a is None and b is None:
                return 0
            else:
                return 1 if a is None and b is not None else -1
        if not a.isdigit() or not b.isdigit():
            a = ord(a)
            b = ord(b)
        result = compare_number(a, b)
        if result != 0:
            return -1 if result < 0 else 1
    return result


class Version:
    """
    版本号对象用于简化版本号比较, 传入字符串"3.1.2.3"构造一个版本号对象，可以通过>, <, =等符号来比较
    两个Version对象的大小，也可以直接将Version同字符串表示的版本号进行比较。
    """

    def __init__(self, version: str):
        self.version = version

    def __eq__(self, other: Union['Version', str]):
        if isinstance(other, str):
            other = Version(other)
        return compare_version(self.version, other.version) == 0

    def __lt__(self, other: Union['Version', str]):
        if isinstance(other, str):
            other = Version(other)
        return compare_version(self.version, other.version) < 0

    def __ne__(self, other: Union['Version', str]):
        return not self.__eq__(other)

    def __gt__(self, other: Union['Version', str]):
        if isinstance(other, str):
            other = Version(other)
        return compare_version(self.version, other.version) > 0

    def __le__(self, other: Union['Version', str]):
        if isinstance(other, str):
            other = Version(other)
        return compare_version(self.version, other.version) <= 0

    def __ge__(self, other: Union['Version', str]):
        if isinstance(other, str):
            other = Version(other)
        return compare_version(self.version, other.version) >= 0

    def __str__(self):
        return self.version


class Time:
    """
    时间对象，传入格式为"2022-01-12 13:14:15"的字符串构造Time对象，两个Time对象
    可以进行大小比较, 可以通过to_timestamp转换为unix系统时间戳
    """

    def __init__(self, _time: str):
        self.date = []
        self.time = []
        _time = _time.split(" ")
        if len(_time) == 1:
            _time = _time[0].split(':')
            self.time = [int(item) for item in _time]
        elif len(_time) == 2:
            _date = _time[0].split('-')
            _time = _time[1].split(':')
            self.date = [int(item) for item in _date]
            self.time = [int(item) for item in _time]
        else:
            raise RuntimeError("Invalid time: %s" % (_time))

    def to_timestamp(self) -> int:
        if len(self.date) != 3 or len(self.time) != 3:
            raise RuntimeError("Invalid time format: %s" % str(self))
        tmp = time.strptime(str(self), "%Y-%m-%d %H:%M:%S")
        return int(time.mktime(tmp))

    @classmethod
    def now(cls, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        return time.strftime(format, time.localtime(time.time()))

    def __eq__(self, other: Union['Time', str]):
        if isinstance(other, str):
            other = Time(other)

        if len(self.date) != len(other.date) or len(self.time) != len(other.time):
            return False

        for a, b in zip(self.date, other.date):
            if a != b:
                return False

        for a, b in zip(self.time, other.time):
            if a != b:
                return False
        return True

    def __lt__(self, other: Union['Time', str]):
        if isinstance(other, str):
            other = Time(other)

        if len(self.date) != len(other.date) or len(self.time) != len(other.time):
            raise RuntimeError("Can't compare, invalid time")

        for a, b in zip(self.date, other.date):
            if a < b:
                return True
        for a, b in zip(self.time, other.time):
            if a < b:
                return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if not self.__lt__(other) and not self.__eq__(other):
            return True
        else:
            return False

    def __le__(self, other):
        if self.__lt__(other) or self.__eq__(other):
            return True
        else:
            return False

    def __ge__(self, other):
        if not self.__lt__(other):
            return True
        else:
            return False

    def __str__(self):
        def convert_generator(version: List[int]):
            for item in version:
                yield str(item)

        result = ':'.join(convert_generator(self.time))
        if len(self.date) != 0:
            date = '-'.join(convert_generator(self.date))
            result = date + ' ' + result
        return result


def get_tmp_dir() -> str:
    """获取临时文件路径"""
    tmp_dir = "./tmp_hypium"
    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)
    return tmp_dir


def get_system_temp_dir():
    import tempfile
    dir_path = os.path.join(tempfile.gettempdir(), "hypium")
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        global hypium_temp_file_dir
        hypium_temp_file_dir = dir_path
        return hypium_temp_file_dir
    except Exception as e:
        return get_tmp_dir()


def get_resource_file(filename: str) -> str:
    "从获取hypium的资源目录获取文件路径"
    cur_dir = os.path.dirname(__file__)
    res_dir = os.path.join(os.path.dirname(cur_dir), "res")
    filepath = os.path.join(res_dir, filename)
    if os.path.isfile(filepath):
        return filepath
    else:
        return None


def parse_json(data):
    if data is False:
        return False
    try:
        data = json.loads(data)
        return data
    except Exception as e:
        return False


def is_file_exist(device, filepath, is_dir=False, expect_echo=None):
    if is_dir:
        cmd = "ls -d %s" % filepath
    else:
        cmd = "ls %s" % filepath
    echo = device.execute_shell_command(cmd).strip()
    if expect_echo is None:
        expect_echo = filepath
    if echo == expect_echo:
        return True
    else:
        return False


def get_device_from_object(obj):
    if hasattr(obj, "device"):
        return obj.device
    elif hasattr(obj, "_device"):
        return obj._device
    else:
        return obj


def get_module_from_driver_impl(driver_impl, module_name):
    """get plugin module from driver implementation"""
    module = getattr(driver_impl, module_name, None)
    if module is None:
        raise RuntimeError("Current driver implementation has not module: " % module_name)
    return module


def get_unused_local_port():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


def is_scale(pos):
    """检查坐标值是否为比例"""
    for item in pos:
        if isinstance(item, float) and 0 < item <= 1:
            return True
    return False


def scale_to_position(pos: tuple, area_size: Union[tuple, Rect]):
    if isinstance(area_size, tuple) or isinstance(area_size, Point):
        width, height = area_size
        area = Rect(right=width, bottom=height)
    elif isinstance(area_size, Rect):
        area = area_size
        width, height = area.get_size()
    else:
        raise TypeError("area size should be (w, h) or Rect")
    x, y = pos
    if isinstance(x, float) and -1 <= x <= 1:
        x = int(x * width)
    if isinstance(y, float) and -1 <= y <= 1:
        y = int(y * height)
    x += area.left
    y += area.top
    return int(x), int(y)


def support_retry(need_retry, interval=0.5):
    def support_retry_deco(func: T) -> T:
        def wrapper(*args, **kwargs):
            start = time.time()
            wait_time = kwargs.get("timeout", 0)
            if "timeout" in kwargs.keys():
                kwargs.pop("timeout")
            result = None
            for _ in range(100):
                result = func(*args, **kwargs)
                if not need_retry(result):
                    return result
                elif wait_time == 0 or time.time() - start > wait_time:
                    return result
            time.sleep(interval)
            return result

        return wrapper

    return support_retry_deco


def push_with_md5_check(device, local_path, remote_path, pushed_flag: str = None):
    if pushed_flag and isinstance(pushed_flag, str):
        if hasattr(device, pushed_flag) and getattr(device, pushed_flag) is True:
            device.log.info(f"Already pushed {local_path}, skip it")
            return

    remote_md5 = device.execute_shell_command(f"md5sum {remote_path}").split()[0].strip()
    with open(local_path, "rb") as f:
        data = f.read()
        md5hash = hashlib.md5(data)
        local_md5 = md5hash.hexdigest()
    device.log.debug("%s local_md5 %s" % (os.path.basename(local_path), local_md5))
    device.log.debug("%s remote_md5 %s" % (os.path.basename(remote_path), remote_md5))
    if local_md5 != remote_md5:
        device.push_file(local_path, remote_path)

    if pushed_flag and isinstance(pushed_flag, str):
        setattr(device, pushed_flag, True)


def check_params(param_type, *params):
    """Check params' type"""
    param_type_name = getattr(param_type, "__name__")
    for item in params:
        if not isinstance(item, param_type):
            raise TypeError(f"param type must be [{param_type_name}]")


def get_readable_timestamp():
    now = datetime.now()  # 获取当前时间
    readable_time = now.strftime("%Y-%m-%d-%H-%M-%S")  # 格式化时间为可读格式
    return readable_time


def get_last_non_blank_line(lines):
    """获取最后一个非空行内容, 如果lines不是字符串则返回空"""
    if not isinstance(lines, str):
        return ""
    lines_list = lines.split("\n")
    for i in range(len(lines_list) - 1, -1, -1):
        line = lines_list[i].strip()
        if len(line) > 0:
            return line
    # 适配\r分隔符
    lines_list = lines.split("\r")
    for i in range(len(lines_list) - 1, -1, -1):
        line = lines_list[i].strip()
        if len(line) > 0:
            return line
    return ""


def grep_one(lines, keyword):
    for line in lines.split("\n"):
        if keyword in line:
            return line
    return ""


def kill_process(pid):
    try:
        if platform.system() == "Windows":
            result = subprocess.run(f"TASKKILL /F /PID {pid} /T".format(pid=pid), capture_output=True)
            echo = result.stdout + result.stderr
            echo = echo.decode(encoding="GB2312", errors="ignore")
            basic_log.info("kill pid return: " + echo)
            if result.returncode != 0:
                basic_log.error(f"Fail to kill pid {pid}")
        else:
            current_pid = os.getpid()
            current_pgid = os.getpgid(current_pid)
            target_pgid = os.getpgid(pid)
            if target_pgid != current_pgid:
                os.killpg(target_pgid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
    except Exception as e:
        basic_log.error(f"kill pid exception: {repr(e)}")


def get_process(pid):
    try:
        import psutil
    except ImportError as e:
        raise ImportError("No psutil, run [python -m pip install psutil] to install it")
    try:
        pid = int(pid)
        return psutil.Process(pid)
    except Exception as e:
        return None


def parse_int(num_str):
    if isinstance(num_str, int):
        return num_str
    elif isinstance(num_str, float):
        return int(num_str)
    elif isinstance(num_str, str):
        num_str = num_str.strip().strip("\"")
    else:
        basic_log.warning(f"Invalid number str: {num_str}")
        return -1
    try:
        return int(num_str)
    except Exception as e:
        basic_log.warning(f"Invalid number str: {num_str}")
        return -1


def parse_float(num_str, default_value=0.0):
    if isinstance(num_str, int):
        return float(num_str)
    elif isinstance(num_str, float):
        return num_str
    elif isinstance(num_str, str):
        num_str = num_str.strip().strip("\"")
    else:
        basic_log.warning(f"Invalid number str: {num_str}")
        return default_value
    try:
        return float(num_str)
    except Exception as e:
        basic_log.warning(f"Invalid number str: {num_str}")
        return default_value


def convert_to_speed(duration, start_point, end_point):
    x1, y1 = start_point
    x2, y2 = end_point
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if duration <= 0:
        raise ValueError("duration must larger than 0")
    return int(distance / duration)


def convert_to_duration(speed, start_point, end_point):
    x1, y1 = start_point
    x2, y2 = end_point
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if speed <= 0:
        raise ValueError("speed must larger than 0")
    return distance / speed


def normalize_device_sn_to_filename(device_sn):
    if "." in device_sn:
        device_sn = device_sn.replace(".", "_")
    if ":" in device_sn:
        device_sn = device_sn.replace(":", "_")
    return device_sn


def add_suffix(file_path, extra_suffix):
    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    base_name_and_suffix_list = base_name.rsplit('.', 1)
    if len(base_name_and_suffix_list) < 2:
        base_name_no_suffix, suffix = base_name, ""
    else:
        base_name_no_suffix, suffix = base_name_and_suffix_list
    if suffix:
        new_filename = base_name_no_suffix + extra_suffix + "." + suffix
    else:
        new_filename = base_name_no_suffix + extra_suffix
    new_file_path = os.path.join(dir_name, new_filename)
    return new_file_path


def get_atomic_driver(driver):
    if hasattr(driver, "driver"):
        return driver.driver
    else:
        return driver
