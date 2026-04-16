from functools import wraps
import time
from hypium.uidriver.interface.iuidriver import IUiDriver
from hypium.exception import *
from hypium.uidriver.logger import hypium_inner_log as basic_log
from hypium.utils.shell import run_command
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


@retry_when_exception(3)
def connect_device(connector: str = "hdc", **kwargs):
    """
    @func 连接设备, 不指定设备sn时默认连接第一个可用设备(该接口仅供快速模式调试脚本使用, 不要在Testcase类中使用)
    @param connector: 设备连接方式, hdc表示使用hdc连接
    @param kwargs: 其他配置参数
                   device_sn: 需要连接的设备sn
                   connector_server: 远程设备服务器地址, 格式为(ip, port)
    """
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
    else:
        raise HypiumNotSupportError("Device type is not support")
    return driver_impl
