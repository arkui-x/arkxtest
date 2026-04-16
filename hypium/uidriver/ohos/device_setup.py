import os.path
import re
import sys

from hypium.uidriver.logger import hypium_inner_log
from hypium.utils import utils


def get_agent_mode_for_old_uitest(device):
    if hasattr(device, "_is_abc") and getattr(device, "_is_abc"):
        setattr(device, "_agent_mode", "abc")
        return "abc"
    else:
        return "hap"


def get_agent_mode_for_new_uitest(device):
    if hasattr(device, "_is_abc") and getattr(device, "_is_abc"):
        setattr(device, "_agent_mode", "bin")
        return "bin"
    else:
        return "hap"


def set_agent_mode_for_old_uitest(device, agent_mode):
    if agent_mode != "hap":
        setattr(device, "_is_abc", True)
        setattr(device, "_agent_mode", "abc")
    else:
        setattr(device, "_agent_mode", "hap")


def set_agent_mode_for_new_uitest(device, agent_mode):
    if agent_mode != "hap":
        setattr(device, "_agent_mode", "bin")
    else:
        setattr(device, "_agent_mode", "hap")


def is_valid_version(version):
    try:
        utils.compare_version(version, "4.1.4.0")
        return True
    except Exception as e:
        hypium_inner_log.warning(f"Invalid version: {version}")
        return False


def _do_parse_uitest_version(raw_uitest_version, grep_last_line=True):
    """
    解析失败返回空字符串
    """
    # 检查版本号数据类型
    if not isinstance(raw_uitest_version, str):
        hypium_inner_log.warning(f"Invalid raw_uitest_version type [{type(raw_uitest_version)}]")
        return ""

    # 首先尝试搜索uitest: 关键字
    uitest_version = utils.grep_one(raw_uitest_version, "uitest:")
    if not uitest_version:
        # 没有找到则执行搜索逻辑无前缀版本号逻辑
        if grep_last_line:
            uitest_version = utils.get_last_non_blank_line(raw_uitest_version)
        else:
            uitest_version = raw_uitest_version

    # 检查是否包含合法版本号
    result = re.search(r"\d+\.\d+\.\d+\.\d+", uitest_version)
    if result is None:
        hypium_inner_log.warning(f"Invalid uitest version [{uitest_version}]")
        return ""
    else:
        uitest_version = result.group()
        return uitest_version


def _parse_uitest_version(raw_uitest_version, default_version="4.1.4.5"):
    # 尝试读取最后一个非空行, 解析uitest版本号
    uitest_version = _do_parse_uitest_version(raw_uitest_version, grep_last_line=True)
    if len(uitest_version) == 0:
        # 返回默认版本号4.1.4.5
        hypium_inner_log.warning(f"Fail to parse version [{raw_uitest_version}], return default {default_version}")
        uitest_version = default_version
    return uitest_version


def get_uitest_version(device):
    if hasattr(device, "_uitest_version") and device._uitest_version:
        return device._uitest_version

    default_version = "4.1.4.5"
    raw_uitest_version = device.execute_shell_command("uitest --version")
    uitest_version = _parse_uitest_version(raw_uitest_version, default_version=default_version)
    if is_valid_version(uitest_version):
        setattr(device, "_uitest_version", uitest_version)
    return uitest_version


def get_auto_agent_mode(device):
    return "bin"


def get_device_agent_mode(device):
    """"""
    if hasattr(device, "_agent_mode"):
        return device._agent_mode
    uitest_version = get_uitest_version(device)
    if utils.compare_version(uitest_version, "4.1.4.0") < 0:
        return get_agent_mode_for_old_uitest(device)
    else:
        return get_agent_mode_for_new_uitest(device)


def set_device_agent_mode(device, agent_mode):
    uitest_version = get_uitest_version(device)
    if utils.compare_version(uitest_version, "4.1.4.0") < 0:
        return set_agent_mode_for_old_uitest(device, agent_mode)
    else:
        return set_agent_mode_for_new_uitest(device, agent_mode)


def is_already_set_agent_mode(device):
    if hasattr(device, "_agent_mode"):
        return True
    if hasattr(device, "_is_abc"):
        return True
    return False


def _setup_ohos_device(device):
    uitest_version = device.execute_shell_command("uitest --version")
    uitest_version = uitest_version.strip()
    device.log.info(uitest_version)
    if uitest_version == "4.1.3.2":
        raise RuntimeError("not support uitest version with version: 4.1.3.2, please use hypium<=5.0.7.200")
    return True



def setup_ohos_device(device):
    """初始化设备端配置"""
    _setup_ohos_device(device)

