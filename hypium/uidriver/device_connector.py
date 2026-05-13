from functools import wraps
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from hypium.uidriver.interface.iuidriver import IUiDriver
from hypium.exception import *
from hypium.uidriver.logger import hypium_inner_log as basic_log
from hypium.utils.shell import run_command
from hypium.uidriver.arkuix.socket_client import DEFAULT_PORT
import shutil
import re
from hypium.dfx import init_status_manager

_env_pool = None

init_status_manager.set_telemetry_config()


def retry_when_exception(retry_times=3, interval=1):
    def _retry(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for i in range(retry_times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    basic_log.warning(f"{func.__name__} failed [{repr(e)}], {i} time retry")
                    time.sleep(interval)
            raise last_err

        return wrapper

    return _retry


def hdc_find_device(hdc_server: tuple):
    if shutil.which("hdc"):
        cmd = "hdc"
    elif shutil.which("hdc_std"):
        cmd = "hdc_std"
    else:
        raise HypiumOperationFailError("No hdc command found")

    if hdc_server:
        ip, port = hdc_server
        if re.search(r"\d+\.\d+\.\d+\.\d+", ip) is None or not isinstance(port, int) or port < 0 or port > 65535:
            raise ValueError("Invalid ip or port: %s" % hdc_server)
        cmd += f" -s {ip}:{port} "

    result = run_command(f"{cmd} list targets")
    if "Empty" in result:
        raise HypiumOperationFailError("No device to connect")
    lines = result.strip().split("\n")
    if len(lines) < 1:
        raise HypiumOperationFailError("No device to connect")
    for line in lines:
        basic_log.debug(f"read devices info: {line}")
        sn_candidate = re.search(r'[\da-zA-Z]+', line)
        if not sn_candidate or len(sn_candidate.group()) < 8:
            sn_candidate = re.search(r'[\d\.\:]+', line)
        if not sn_candidate or len(sn_candidate.group()) < 8:
            basic_log.warning(f"Skip invalid sn: {line}")
            continue
        basic_log.info(f"No device sn passed, using first device sn: {line}")
        return line.strip()
    raise HypiumOperationFailError("No device to connect")


def _find_user_config_xml() -> str:
    try:
        preferred_path = os.path.abspath(os.path.join(os.getcwd(), "..", "config", "user_config.xml"))
        if os.path.isfile(preferred_path):
            return preferred_path
    except Exception:
        pass

    candidates = []

    main_script = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if main_script:
        candidates.append(os.path.dirname(main_script))

    try:
        candidates.append(os.getcwd())
    except Exception:
        pass

    seen = set()
    for start_dir in candidates:
        current_dir = os.path.abspath(start_dir)
        while current_dir and current_dir not in seen:
            seen.add(current_dir)
            config_path = os.path.join(current_dir, "config", "user_config.xml")
            if os.path.isfile(config_path):
                return config_path
            direct_path = os.path.join(current_dir, "user_config.xml")
            if os.path.isfile(direct_path):
                return direct_path
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
            current_dir = parent_dir
    return ""


def _coerce_xml_scalar(text: str):
    value = (text or "").strip()
    if value == "":
        return ""

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if re.fullmatch(r"[-+]?\d+", value):
        try:
            return int(value)
        except Exception:
            return value

    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", value):
        try:
            return float(value)
        except Exception:
            return value

    return value


def _validate_arkuix_config(config: dict) -> None:
    """验证 arkuix 配置的合法性。
    
    Args:
        config: arkuix 配置字典
        
    Raises:
        HypiumParamError: 配置值无效
    """
    if "platform" in config:
        platform = config["platform"]
        if platform not in ("android", "ios"):
            raise HypiumParamError(
                msg=f"arkuix config field 'platform' must be 'android' or 'ios', got '{platform}'"
            )
    
    if "port" in config:
        try:
            port = int(config["port"])
            if port < 0 or port > 65535:
                raise ValueError("out of range")
        except (TypeError, ValueError):
            raise HypiumParamError(
                msg=f"arkuix config field 'port' must be an integer between 0 and 65535, got '{config['port']}'"
            )
    
    if "host" in config:
        host = config["host"]
        if not isinstance(host, str) or not host.strip():
            raise HypiumParamError(
                msg=f"arkuix config field 'host' must be a non-empty string, got '{host}'"
            )
    
    if "device_id" in config:
        device_id = config["device_id"]
        if not isinstance(device_id, str) or not device_id.strip():
            raise HypiumParamError(
                msg=f"arkuix config field 'device_id' must be a non-empty string, got '{device_id}'"
            )
    
    for timeout_key in ("connect_timeout", "recv_timeout"):
        if timeout_key in config:
            try:
                timeout = float(config[timeout_key])
                if timeout <= 0:
                    raise ValueError("must be positive")
            except (TypeError, ValueError):
                raise HypiumParamError(
                    msg=f"arkuix config field '{timeout_key}' must be a positive number, got '{config[timeout_key]}'"
                )


def _load_cross_platform_from_user_config_xml() -> dict:
    config_path = _find_user_config_xml()
    if not config_path:
        return {}

    try:
        root = ET.parse(config_path).getroot()
    except Exception as error:
        basic_log.warning(f"parse user_config.xml failed: {error}")
        return {}

    arkuix_node = root.find("./environment/arkuix")
    if arkuix_node is None:
        return {}

    supported_keys = {
        "platform", "host", "port", "device_id",
        "connect_timeout", "recv_timeout"
    }

    result = {}
    for key in supported_keys:
        node = arkuix_node.find(key)
        if node is not None:
            result[key] = _coerce_xml_scalar(node.text)

    # Validate configuration values
    try:
        _validate_arkuix_config(result)
    except HypiumParamError as e:
        basic_log.error(f"arkuix config validation failed: {e}")
        raise

    return result

def _make_arkuix_args(cross_platform_cfg: dict):
    arkuix_kwargs = dict(cross_platform_cfg or {})
    host = arkuix_kwargs.pop("host", "127.0.0.1")
    port = arkuix_kwargs.pop("port", DEFAULT_PORT)
    platform = arkuix_kwargs.pop("platform", None)
    arkuix_kwargs.setdefault("connect_timeout", 10)
    arkuix_kwargs.setdefault("recv_timeout", 60)
    return host, port, platform, arkuix_kwargs


@retry_when_exception(3)
def connect_device(connector: str = "hdc", **kwargs):
    """
    @func 连接设备, 不指定设备sn时默认连接第一个可用设备(该接口仅供快速模式调试脚本使用, 不要在Testcase类中使用)
    @param connector: 设备连接方式, 默认 hdc；跨平台 Android/iOS 由配置文件决定
    @param kwargs: 其他配置参数
                   device_sn: 需要连接的设备sn
                   connector_server: 远程设备服务器地址, 格式为(ip, port)
    """
    cross_platform_cfg = _load_cross_platform_from_user_config_xml()
    configured_platform = cross_platform_cfg.get("platform", None)
    if configured_platform in ("android", "ios"):
        basic_log.info(f"cross_platform config selects {configured_platform}, use arkuix device connector")
        from hypium.uidriver.arkuix.arkuix_device import ArkUIXDevice
        host, port, platform, arkuix_kwargs = _make_arkuix_args(cross_platform_cfg)
        return ArkUIXDevice(host, port, platform, **arkuix_kwargs)

    global _env_pool
    device_sn = kwargs.get("device_sn", None)
    connector_server = kwargs.get("connector_server")
    if device_sn is None:
        if connector == "hdc":
            device_sn = hdc_find_device(connector_server)
        else:
            raise HypiumParamError(msg=f"invalid connector: {connector}, support [hdc]")
    from xdevice import DeviceNode
    from xdevice import DeviceSelector
    from xdevice import EnvPool
    if _env_pool is None:
        node = DeviceNode(f"usb-{connector}").build_connector(connector)  # 只允许初始化一次
        if connector_server:
            node.add_address(connector_server[0], str(connector_server[1]))
        pool = EnvPool(**kwargs)
        pool.init_pool(node)
        _env_pool = pool
    selector = DeviceSelector().add_device_sn(device_sn)
    device = _env_pool.get_device(selector)
    if device is None:
        raise HypiumOperationFailError(f"Fail to get device, connector {connector}, params {kwargs}")
    return device


def create_driver_impl(device, agent_mode: str = 'auto', **kwargs) -> IUiDriver:
    """
    根据设备类型, 创建不同系统的driver实现对象, 传入device设备对象创建driver
    """
    device_class_type = type(device)
    device_class_name = device_class_type.__name__
    if device_class_name == "Device":
        from hypium.uidriver.ohos.uidriver import OHOSDriver
        driver_impl = OHOSDriver(device, agent_mode, **kwargs)
    elif device_class_name == "ArkUIXDevice":
        from hypium.uidriver.arkuix.arkuix_driver_impl import ArkUIXDriverImpl
        driver_impl = ArkUIXDriverImpl(device, **kwargs)
    else:
        raise HypiumNotSupportError("Device type is not support")
    return driver_impl
