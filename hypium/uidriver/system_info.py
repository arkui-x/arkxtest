from typing import Tuple, Union
from hypium.uidriver.common import device_type_helper
from hypium.uidriver.ohos import system_info as ohos_system_info


def get_os_info(device) -> Tuple[str, str]:
    if device_type_helper.is_ohos_device(device):
        return ohos_system_info.get_os_info(device)
    else:
        raise ValueError("Unsupported device type")

def get_api_level(device):
    if device is None:
        return 8

    if hasattr(device, "oh_api_level"):
        return device.oh_api_level
    if device_type_helper.is_ohos_device(device):
        api_level = ohos_system_info.get_api_level(device)
    else:
        raise ValueError("Unsupported device type")
    if api_level < 0:
        device.log.error("Fail to get device api level")
    setattr(device, "oh_api_level", api_level)
    return api_level

def is_valid_device(device):
    return True