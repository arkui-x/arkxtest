"""
description: 读取device对象类型信息
"""
def is_ohos_device(device):
    device_type = type(device).__name__
    return device_type == "Device"

