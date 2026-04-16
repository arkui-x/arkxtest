import argparse
import base64
import json
import datetime
import os.path
import time
import traceback
from pathlib import Path

from xdevice import Tracker

# 隐私声明模块配置参数
DEBUG = False
PRIVACY_CONFIRMED = False
PROMPT_SHOW = False
CONFIRMED_INFO = "\nConfirmed: y"
DENIED_INFO = "\nConfirmed: n"
USER_DATA_DIR = '.hypium'  # 隐私协议写入目录
HYPIUM_CONFIG_FILE_NAME = "hypium_config"
TELEMETRY_DISABLE_INFO = "telemetry_disable"

privacy_doc_basic_content = "隐私协议加载失败"


def load_privacy_content():
    global privacy_doc_basic_content
    dir_path = os.path.dirname(__file__)
    privacy_file_name = "privacy_policy.md"
    privacy_file_path = os.path.join(dir_path, privacy_file_name)
    with open(privacy_file_path, "r", encoding="utf-8") as f:
        privacy_doc_basic_content = f.read()


load_privacy_content()

# 隐私声明文档
privacy_doc = privacy_doc_basic_content + "\n同意隐私声明并继续请输入y, 不同意终止请输入n:"


def run_when_debug(func):
    def wrapper(*args, **kwargs):
        if not DEBUG:
            return None
        return func(*args, **kwargs)

    return wrapper


class SimpleLogger:

    # 日志信息仅在DEBUG模式下打印
    @run_when_debug
    @staticmethod
    def log_info(info):
        print(info)

    @run_when_debug
    @staticmethod
    def log_error(info):
        print(info)

    @run_when_debug
    @staticmethod
    def log_debug(info):
        print(info)


def advanced_deobfuscate(s, data):
    try:
        decoded = base64.b85decode(s.encode('utf-8'))
        data_bytes = str(data).encode('utf-8')
        deobfuscated = bytes([decoded[i] ^ data_bytes[i % len(data_bytes)] for i in range(len(decoded))])
        return deobfuscated.decode('utf-8')
    except Exception:
        return s


def is_privacy_confirmed(privacy_file_content):
    return privacy_file_content.startswith(privacy_doc + CONFIRMED_INFO)


def get_timestamp(privacy_file_content):
    try:
        last_line = privacy_file_content.split("\n")[-1]
        dt_from_iso = datetime.datetime.fromisoformat(last_line.strip())
        return dt_from_iso
    except Exception:
        return datetime.datetime.now()


def read_data_config():
    try:
        file_path = os.path.join(os.path.dirname(__file__), "data")
        with open(file_path, 'r', encoding="utf-8") as f:
            data = f.read()
        description = "hypium_analysis_info_description"
        info = advanced_deobfuscate(data, description)
        config_info = json.loads(info)
    except Exception as e:
        SimpleLogger.log_error("Fail to load config file: %s" % repr(e))
        config_info = {}
    return config_info


def get_current_timestamp():
    return datetime.datetime.now().isoformat()


def get_confirmed_privacy_content():
    return privacy_doc + CONFIRMED_INFO


def get_denied_privacy_content():
    return privacy_doc + DENIED_INFO


class HypiumInitConfigInfo:

    def __init__(self):
        self.model_init = ""
        self.privacy_confirmed = ""
        self.version = ""
        self.timestamp = ""

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict):
        item = cls()
        for key, value in data.items():
            item.__dict__[key] = value
        return item


class InitConfigFileManager:

    def __init__(self):
        self.config_file_init = False
        self.config_data = HypiumInitConfigInfo()
        self.config_file_name = HYPIUM_CONFIG_FILE_NAME
        self.load()

    def preprocess_file_to_write(self, file_content: str):
        file_content_binary = file_content.encode(encoding="utf-8")
        return base64.b64encode(file_content_binary)

    def disable_privacy(self):
        self.config_data.privacy_confirmed = TELEMETRY_DISABLE_INFO
        self.save()

    def enable_privacy(self):
        self.config_data.privacy_confirmed = get_confirmed_privacy_content()
        self.save()

    def preprocess_file_from_read(self, file_content):
        return base64.b64decode(file_content).decode(encoding="utf-8")

    def write_file_to_user_dir(self, filename: str, content: str = '') -> str:
        """
        向用户目录写入文件
        """
        # 获取用户主目录
        try:
            user_dir = Path.home()
            # 构建完整路径
            file_path = os.path.join(user_dir, USER_DATA_DIR, filename)
            # 确保父目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # 创建并写入文件
            data = self.preprocess_file_to_write(content)
            with open(file_path, 'wb') as f:
                f.write(data)
            return file_path
        except Exception:
            SimpleLogger.log_error("Fail to write file: %s" % traceback.format_exc())
            return ""

    def read_file_from_user_dir(self, filename: str):
        """
        从hypium数据目录下读取指定文件内容
        """
        # 获取用户主目录
        user_dir = Path.home()
        # 构建完整路径
        file_path = os.path.join(user_dir, USER_DATA_DIR, filename)
        if not os.access(file_path, os.R_OK):
            return ""

        try:
            # 创建并写入文件
            with open(file_path, 'rb') as f:
                return self.preprocess_file_from_read(f.read())
        except Exception:
            SimpleLogger.log_error("Fail to write file: %s" % traceback.format_exc())
            return ""

    def load(self):
        """
        加载初始化文件
        """
        try:
            data = self.read_file_from_user_dir(self.config_file_name)
            self.config_data = HypiumInitConfigInfo.from_dict(json.loads(data))
            self.config_file_init = True
        except Exception as e:
            SimpleLogger.log_error("Fail to load config file: %s" % repr(e))

    def save(self):
        """
        保存初始化文件
        """
        try:
            self.config_data.timestamp = get_current_timestamp()
            self.write_file_to_user_dir(self.config_file_name, json.dumps(self.config_data.to_dict()))
        except Exception as e:
            SimpleLogger.log_error("Fail to load config file: %s" % repr(e))

    def request_privacy_confirm(self, cmd_confirm_privacy=False):
        if cmd_confirm_privacy:
            return get_confirmed_privacy_content()
        print(privacy_doc)
        result = input()
        if result == 'y':
            return get_confirmed_privacy_content()
        else:
            return get_denied_privacy_content()

    def do_model_init(self, confirm_privacy=False):
        print("Start to init models")
        try:
            from hypium_turbo.utils.init_status_manager import init_models
            self.config_data.model_init = init_models()
            if not self.config_data.model_init:
                print("Invalid model files, maybe hypium-turbo-model is not installed or corrupted, "
                      "please install hypium-turbo-model or reinstall it")
                return False
        except ImportError:
            print("hypium-turbo not install, please install hypium-turbo to init models")
            return False
        self.save()
        return True

    def get_privacy_url(self):
        return read_data_config().get("privacy_url", "")

    def get_privacy_confirm_status(self):
        privacy_data = self.config_data.privacy_confirmed
        return privacy_data != TELEMETRY_DISABLE_INFO

    def set_tracker_config(self, privacy_confirm_status):
        try:
            Tracker.set_privacy_enable(privacy_confirm_status)
            SimpleLogger.log_info("set tracker status: %s" % privacy_confirm_status)
            if privacy_confirm_status:
                config = read_data_config()
                Tracker.set_testing_analysis_config(config.get("url", ""), config.get("info1", ""))
        except Exception as e:
            SimpleLogger.log_error("Fail to set telemetry config: %s" % repr(e))

    def check_init_status(self, **kwargs):
        if self.config_data.model_init:
            return True
        else:
            return False

    def do_init(self, confirm_privacy, **kwargs):
        if self.config_data.model_init:
            return True
        init_result = self.do_model_init(confirm_privacy)
        self.set_tracker_config(self.get_privacy_confirm_status())
        return init_result


def set_telemetry_config():
    manager = InitConfigFileManager()
    manager.set_tracker_config(manager.get_privacy_confirm_status())


def check_init_status(**kwargs):
    return InitConfigFileManager().check_init_status(**kwargs)


def init_command(models: str, enable_telemetry: bool = False) -> None:
    """
    Initialize with given models and optional telemetry setting
    """
    if models != "models":
        print("Invalid argument [%s] for init command, only support [models]" % models)
        return
    if enable_telemetry:
        print("User enable telemetry by command-line option")
    if InitConfigFileManager().do_init(enable_telemetry):
        print("init models successfully")
    else:
        print("Fail to init models")


def telemetry_command(action: str) -> None:
    """
    Handle telemetry enable/disable/status commands
    """
    if action == "enable":
        print("Enable telemetry")
        InitConfigFileManager().enable_privacy()
        print("Telemetry enable status: %s" % InitConfigFileManager().get_privacy_confirm_status())
        print("For the Privacy Policy, please refer to %s" % InitConfigFileManager().get_privacy_url())
    elif action == "disable":
        print("Disable telemetry")
        InitConfigFileManager().disable_privacy()
        print("Telemetry enable status: %s" % InitConfigFileManager().get_privacy_confirm_status())
    elif action == "status":
        print("Telemetry enable status: %s" % InitConfigFileManager().get_privacy_confirm_status())
    else:
        print(f"Unknown telemetry action: {action}")


def main(get_help_info=False):
    parser = argparse.ArgumentParser(prog="python -m hypium",
                                     description="hypium command line tools")
    subparsers = parser.add_subparsers(dest="command")

    # Telemetry command
    telemetry_parser = subparsers.add_parser("telemetry", help="Manage telemetry settings")
    telemetry_parser.add_argument("action",
                                  choices=["enable", "disable", "status"],
                                  help="Telemetry action to perform")
    if get_help_info:
        return parser.format_help()

    args = parser.parse_args()

    if args.command == "telemetry":
        telemetry_command(args.action)
    return ""
