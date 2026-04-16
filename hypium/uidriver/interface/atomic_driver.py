from abc import ABC, abstractmethod
from typing import List

from hypium.model.driver_config import DriverConfig
from hypium.uidriver.interface.log import ILog
from hypium.uidriver.interface.uitree import IUiComponent


class IComponentFinder(ABC):

    @abstractmethod
    def is_selector_support(self, selector) -> bool:
        pass

    @abstractmethod
    def find_component(self, selector, timeout) -> IUiComponent:
        pass

    @abstractmethod
    def find_components(self, selector, timeout) -> List[IUiComponent]:
        pass


class IAtomicDriver(IComponentFinder):

    @property
    @abstractmethod
    def config(self) -> DriverConfig:
        pass

    @property
    @abstractmethod
    def display_size(self):
        pass
    @property
    @abstractmethod
    def display_rotation(self):
        pass

    @property
    @abstractmethod
    def device_type(self):
        pass

    @property
    @abstractmethod
    def os_type(self) -> str:
        pass

    @property
    @abstractmethod
    def log(self) -> ILog:
        pass

    @property
    @abstractmethod
    def device_sn(self) -> str:
        pass

    @abstractmethod
    def execute_shell_command(self, cmd, timeout: float = 60):
        pass

    @abstractmethod
    def execute_connector_command(self, cmd, timeout: float = 60) -> str:
        pass

    def exectue_connector_command(self, cmd, timeout: float = 60) -> str:
        return self.execute_connector_command(cmd, timeout)

    def log_info(self, *args, **kwargs):
        return self.log.info(*args, **kwargs)

    def log_warning(self, *args, **kwargs):
        return self.log.debug(*args, **kwargs)

    def log_error(self, *args, **kwargs):
        return self.log.debug(*args, **kwargs)

    def log_debug(self, *args, **kwargs):
        return self.log.debug(*args, **kwargs)

    @abstractmethod
    def get_uitest_cmd(self):
        """返回设备端uitest命令"""
        pass

