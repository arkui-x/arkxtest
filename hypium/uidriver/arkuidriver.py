import os
import time
import weakref
from typing import List, Tuple, TypeVar
from hypium.uidriver.interface.log import ILog
from .common import config_helper
from .common.uicomponent_helper import MultiModeComponentFinder
from .frontend_api import FrontEndClass, frontend_api, \
    get_api_level, get_os_info, set_using_api_level, do_hypium_rpc, ApiConfig
from .interface.atomic_driver import IComponentFinder, IAtomicDriver
from .interface.uitree import IUiComponent
from .uiwindow import UiWindow
from .shell import Shell
from hypium.exception import *
from .pointer_matrix import PointerMatrix
from hypium.model.basic_data_type import *
from .by import By
from hypium.utils.test_api import record_time
from ..model.driver_config import DriverConfig

try:
    from devicetest.record_actions.record_action import record_action
except Exception:
    def record_action(func):
        return func

T = TypeVar('T')


class UiTestComponentFinder(IComponentFinder):

    def __init__(self, driver):
        self._driver = driver

    def is_selector_support(self, selector) -> bool:
        return isinstance(selector, By)

    def find_component(self, selector, timeout):
        return do_hypium_rpc(ApiConfig(since=9, hmos_since=8),
                             "UiDriver.waitForComponent", self._driver, selector, int(timeout * 1000))

    def find_components(self, selector, timeout):
        return do_hypium_rpc(ApiConfig(since=8), "UiDriver.findComponents", self._driver, selector)


class ArkUiMultiModeComponentFinder(MultiModeComponentFinder):

    def __init__(self, driver: IAtomicDriver, uitree_finder, uitest_finder):
        self._uitree_finder = uitree_finder
        self._uitest_finder = uitest_finder
        self._driver = driver

    @classmethod
    def create(cls, driver) -> 'ArkUiMultiModeComponentFinder':
        from hypium.uidriver.uitree import UiTreeComponentFinder
        return ArkUiMultiModeComponentFinder(driver,
                                             UiTreeComponentFinder(driver),
                                             UiTestComponentFinder(driver))

    @property
    def sorted_finders(self):
        """返回根据指定配置策略排序后的finder"""
        if self._driver.config.component_find_backend == "uitree":
            return self._uitree_finder, self._uitest_finder
        else:
            return self._uitest_finder, self._uitree_finder


class ArkUiDriver(FrontEndClass, IAtomicDriver):

    def __init__(self, backend_obj_ref):
        FrontEndClass.__init__(self, backend_obj_ref)
        self._device_type = ""
        self._component_finder = None

    def recover(self, device=None):
        if device:
            return self.resolve(device)
        else:
            return self.resolve(self._device)

    def resolve(self, device):
        self._resolved = True
        return True

    def activate(self, backend_obj_ref, device):
        super().activate(backend_obj_ref, device)
        if not self._component_finder:
            self._component_finder = ArkUiMultiModeComponentFinder.create(weakref.proxy(self))

    def deactivate(self):
        super().deactivate()

    def _screenshot(self, image_path: str):
        timestamp = int(time.time() * 1000)
        tmp_path = self.get_device_tmp_path() + "/%s.jpeg" % timestamp
        screenshot_msg = self.screenCap(tmp_path)
        self._device.pull_file(tmp_path, image_path, timeout=10 * 1000)
        if not os.path.exists(image_path):
            if "success" not in screenshot_msg:
                raise HypiumOperationFailError("Fail to get screenshot: %s" % screenshot_msg)
            else:
                raise HypiumOperationFailError(
                    "Fail to pull screenshot to: [%s], please check if the path exists" % image_path)
        self.execute_shell_command("rm %s" % tmp_path, timeout=10)
        return image_path

    def screenshot(self, image_path: str):
        last_err = None
        for _ in range(self.config.screenshot_retry_times):
            try:
                return self._screenshot(image_path)
            except Exception as e:
                self.log_warning("Fail to screenshot: %s" % repr(e))
                last_err = e
        raise last_err


    @staticmethod
    @frontend_api(since=8)
    def create(device) -> 'ArkUiDriver':
        pass

    @frontend_api(since=8)
    def delayMs(self, duration: int) -> None:
        pass

    @record_action
    @record_time
    def findComponent(self, by: By) -> IUiComponent:
        comp = self._component_finder.find_component(by, 0)
        if comp is not None and not hasattr(comp, "driver"):
            setattr(comp, "driver", weakref.proxy(self))
        return comp

    @frontend_api(since=9)
    def findWindow(self, filter: WindowFilter) -> UiWindow:
        pass

    @record_time
    def findComponents(self, by: By) -> List[IUiComponent]:
        return self._component_finder.find_components(by, 0)

    def assertComponentExist(self, by: By) -> None:
        assert self._component_finder.find_component(by, 0)

    @frontend_api(since=8)
    def pressBack(self) -> None:
        pass

    def pressHome(self) -> None:
        if self.device_type == DeviceType.WEARABLE:
            return self.triggerKey(KeyCode.POWER.value)
        else:
            return do_hypium_rpc(ApiConfig(since=9), "UiDriver.pressHome", self)

    @record_time
    @frontend_api(since=8)
    def triggerKey(self, keyCode: int) -> None:
        pass

    @frontend_api(since=9)
    def triggerCombineKeys(self, key_code: int, key_code2: int, key_code3: int = None) -> None:
        pass

    @frontend_api(since=8)
    def click(self, x: int, y: int) -> None:
        pass

    @frontend_api(since=8)
    def doubleClick(self, x: int, y: int) -> None:
        pass

    @frontend_api(since=8)
    def longClick(self, x: int, y: int) -> None:
        pass

    @frontend_api(since=8)
    def swipe(self, startx: int, starty: int, endx: int, endy: int, speed: int) -> None:
        pass

    @frontend_api(since=8)
    def setDisplayRotation(self, rotation: DisplayRotation) -> None:
        pass

    @frontend_api(since=8)
    def getDisplayRotation(self) -> DisplayRotation:
        pass

    @frontend_api(since=9)
    def setDisplayRotationEnabled(self, enabled) -> None:
        pass

    @frontend_api(since=10)
    def uiEventObserverOnce(self, showType: str):
        pass

    @frontend_api(since=10)
    def getRecentUiEvent(self, timeout: int):
        pass

    @frontend_api(since=9)
    def fling(self, start: Point, end: Point, step_len: int, speed: int):
        pass

    @frontend_api(since=9)
    def getDisplaySize(self) -> Point:
        pass

    @frontend_api(since=9)
    def getDisplayDensity(self) -> Point:
        pass

    def inputText(self, pos: Point, text: str, mode=None) -> None:
        if not mode:
            return do_hypium_rpc(ApiConfig(since=9), "Driver.inputText", self, pos, text)
        else:
            return do_hypium_rpc(ApiConfig(since=20), "Driver.inputText", self, pos, text, mode)

    def screenCap(self, savePath: str):
        if self.get_os_type() == OSType.OHOS:
            cmd = "snapshot_display -f %s" % savePath
        else:
            raise HypiumNotSupportError(self.get_os_type())
        return self.execute_shell_command(cmd)

    @record_time
    def waitForComponent(self, by: By, time_ms: int) -> IUiComponent:
        comp = self._component_finder.find_component(by, time_ms / 1000)
        if comp is not None and not hasattr(comp, "driver"):
            setattr(comp, "driver", weakref.proxy(self))
        return comp

    @record_time
    @frontend_api(since=8, compatibility=True)
    def waitForIdle(self, idleTime_ms: int, timeout_ms: int) -> None:
        pass

    @frontend_api(since=9)
    def wakeUpDisplay(self) -> None:
        pass

    @frontend_api(since=9, hmos_since=8)
    def drag(self, starx: int, starty: int, endx: int, endy: int, speed: int):
        pass

    @frontend_api(since=20)
    def dragBetween(self, start: Point, end: Point, speed: int, duration: int):
        pass

    @frontend_api(since=9)
    def injectMultiPointerAction(self, pointers: PointerMatrix, speed: int):
        pass

    @frontend_api(since=10)
    def mouseClick(self, p: Point, btnId: MouseButton, key1: int = None, key2: int = None):
        pass

    @frontend_api(since=10)
    def mouseScroll(self, p: Point, down: bool, d: int, key1: int = None, key2: int = None, speed: int = None):
        pass

    @frontend_api(since=10)
    def mouseDrag(self, start: Point, end: Point, speed: int):
        pass

    @frontend_api(since=10)
    def mouseMoveTo(self, p: Point):
        pass

    @frontend_api(since=10)
    def mouseMoveWithTrack(self, start: Point, end: Point, speed: int):
        pass

    def create_pointer_matrix(self, fingers: int, steps: int) -> 'PointerMatrix':
        """创建手势路径"""
        return PointerMatrix.create(self._device, fingers, steps)

    def get_shell_instance(self):
        if not hasattr(self, 'shell'):
            self.shell = Shell(self._device)
            return self.shell
        return self.shell

    # 获取系统名称, 代替get_os
    def get_os_type(self) -> str:
        return self.get_os()

    def get_device_tmp_path(self) -> str:
        return "/data/local/tmp"

    def get_device_sn(self) -> str:
        return self._device.device_sn

    def get_api_level(self):
        return get_api_level(self._device)

    def get_os_info(self) -> Tuple[str, str]:
        return get_os_info(self._device)

    def get_os(self):
        return self.get_shell_instance().get_os()

    def log_info(self, *args, **kwargs):
        self._device.log.info(*args, **kwargs)

    def log_warning(self, *args, **kwargs):
        self._device.log.warning(*args, **kwargs)

    def log_error(self, *args, **kwargs):
        self._device.log.error(*args, **kwargs)

    def log_debug(self, *args, **kwargs):
        self._device.log.debug(*args, **kwargs)

    def get_uitest_cmd(self):
        return "uitest"

    def execute_connector_command(self, cmd, timeout: float = 60) -> str:
        echo = self._device.connector_command(cmd, timeout=int(timeout * 1000))
        if not isinstance(echo, str):
            return ""
        else:
            return echo

    def execute_shell_command(self, cmd, timeout: float = 60):
        echo = self._device.execute_shell_command(cmd, timeout=int(timeout * 1000))
        if not isinstance(echo, str):
            return ""
        else:
            return echo

    @property
    def display_size(self):
        return self.getDisplaySize()

    @property
    def display_rotation(self):
        return self.getDisplayRotation()

    @property
    def device_type(self):
        if self._device_type:
            return self._device_type
        echo = self.execute_shell_command("param get const.product.devicetype").strip()
        if 0 < len(echo) < 10:
            self._device_type = echo
            return self._device_type
        else:
            self.log_warning("Invalid devicetype %s" % echo)
            return "phone"

    @property
    def os_type(self) -> str:
        return self.get_os_type()

    @property
    def log(self) -> ILog:
        return self._device.log

    @property
    def device_sn(self) -> str:
        return self._device.device_sn

    def is_selector_support(self, selector) -> bool:
        return self._component_finder.is_selector_support(selector)

    def find_component(self, selector, timeout) -> IUiComponent:
        return self._component_finder.find_component(selector, timeout)

    def find_components(self, selector, timeout) -> List[IUiComponent]:
        return self._component_finder.find_components(selector, timeout)

    def dump_layout_debug_info(self, max_len=40):
        window_info = self.execute_shell_command(
            f"hidumper -s WindowManagerService -a '-a' | head -n {max_len}")
        self.log_debug(window_info)

    @property
    def config(self) -> DriverConfig:
        return config_helper.get_config(self._device)

    @frontend_api(since=16)
    def touchPadMultiFingerSwipe(self, fingers: int, direction: int, option: TouchPadSwipeOptions = None) -> None:
        pass

    @frontend_api(since=16)
    def penClick(self, p: Point) -> None:
        pass

    @frontend_api(since=16)
    def penLongClick(self, p: Point, pressure: float = None) -> None:
        pass

    @frontend_api(since=16)
    def penDoubleClick(self, p: Point) -> None:
        pass

    @frontend_api(since=16)
    def penSwipe(self, start: Point, end: Point, speed: int = None, pressure: float = None) -> None:
        pass

    @frontend_api(since=16)
    def injectPenPointerAction(self, pointers: PointerMatrix, speed: int = None, pressure: float = None) -> None:
        pass

    @frontend_api(since=20)
    def crownRotate(self, d: int, speed: int = None):
        pass


# register type and creator
FrontEndClass.frontend_type_creators['UiDriver'] = lambda ref: ArkUiDriver(ref)
FrontEndClass.frontend_type_creators['Driver'] = lambda ref: ArkUiDriver(ref)
FrontEndClass.return_handlers['getDisplayRotation'] = lambda value: DisplayRotation(value)


class OSAwBase:
    """AWBase on UiDriver"""

    def __init__(self, driver: ArkUiDriver):
        self.driver = driver

    @property
    def _device(self):
        return self.driver._device

    @property
    def device_sn(self):
        return self.driver._device.device_sn
