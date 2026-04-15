from hypium.utils import utils
import sys

def reset_device(device):
    setattr(device, "hypium_setup_finished", False)
    setattr(device, "_uitest_version", "")

def setup_device(device):
    """
    根据设备系统类型, 执行设备的预置操作
    """
    device_type_name = type(device).__name__
    if getattr(device, "hypium_setup_finished", None):
        return
    if device_type_name == "Device":
        from hypium.uidriver.ohos import device_setup as ohos_setup
        ohos_setup.setup_ohos_device(device)
    else:
        device.log.info("No setup for ohos")
    setattr(device, "hypium_setup_finished", True)


def get_device_agent_mode(device):
    from hypium.uidriver.ohos.device_setup import get_device_agent_mode as ohos_get_device_agent_mode
    return ohos_get_device_agent_mode(device)


def set_device_agent_mode(device, agent_mode):
    from hypium.uidriver.ohos.device_setup import set_device_agent_mode as ohos_set_device_agent_mode
    return ohos_set_device_agent_mode(device, agent_mode)


def is_already_set_agent_mode(device):
    from hypium.uidriver.ohos.device_setup import is_already_set_agent_mode as ohos_is_already_set_agent_mode
    return ohos_is_already_set_agent_mode(device)
