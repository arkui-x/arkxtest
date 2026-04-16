from typing import Optional
from xdevice import Variables
from hypium.utils.logger import basic_log
from hypium.model.driver_config import UiDriverPropertyInDevice, DriverConfig

def get_config(device) -> DriverConfig:
    """读取driver配置"""
    config = getattr(device, UiDriverPropertyInDevice.CONFIG, None)
    if config:
        return config
    else:
        # 没有配置项则创建空配置项
        config = DriverConfig()
        setattr(device, UiDriverPropertyInDevice.CONFIG, config)
        return config
