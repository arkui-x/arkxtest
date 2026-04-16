#!/usr/bin/env python
import json
import math
import os
import random
import time
import re
import warnings
from functools import wraps
from typing import List, Union, Tuple

from hypium.dfx.tracker import Tracker, TrackerEvent
from hypium.uidriver.interface import IUiDriver
from hypium.uidriver.interface.uitree import ISelector, IUiComponent

try:
    from devicetest.controllers.cv import cv
    import cv2
except ImportError as e_no_cv:
    from hypium.utils.fake_module import FakeModule

    cv2 = FakeModule("please install opencv-python to use this function")
from devicetest.core.test_case import MESSAGE, ACTUAL, EXPECT

try:
    from devicetest.record_actions.record_action import record_action
except Exception:
    def record_action(func):
        return func
from hypium.utils.cv import CVBasic
from hypium.exception import *
from hypium.utils import utils
from hypium.uidriver.ohos import device_setup as device_helper
from hypium.uidriver.by import By
from hypium.uidriver.arkuidriver import ArkUiDriver, OSAwBase
from hypium.utils.typevar import T
from hypium.uidriver.uicomponent import UiComponent
from hypium.uidriver.arkuidriver import ArkUiDriver, OSAwBase
from hypium.uidriver.uiwindow import UiWindow
from hypium.uidriver.gesture import Gesture, gestures_to_pointer_matrix
from hypium.model.basic_data_type import *
from hypium.uidriver.ohos import app_manager
from hypium.utils.event_manager import EventManager
from hypium.uidriver.common.enhanced_component_finder import _convert_to_uicomponent

INPUT_TEXT_WAIT_TIME = 1
DEFAULT_IDLE_TIME = 0.2
DEFAULT_SLIDE_TIME = 0.3
MAX_TIMEOUT = 60
DEFAULT_TIMEOUT = 10
WAIT_FOR_INSTALL_TIME = 3
FAST_SWIPE_TIME = 0.25
NAV_GESTURE_SPEED = 8000
# 连续滑动时滑动间隔(避免滑动太快不符合正常人操作)
SWIPE_INTERVAL = 0.5


def _ohos_dump_window_info(driver: ArkUiDriver, max_len=20):
    if driver.get_os_type() == OSType.OHOS:
        window_info = driver.execute_shell_command(f"hidumper -s WindowManagerService -a '-a' | head -n {max_len}")
        driver.log_info(window_info)


def _generate_drag_position(driver: ArkUiDriver, start: Union[ISelector, tuple], end: Union[ISelector, tuple],
                            area: Union[ISelector, IUiComponent] = None) -> Tuple[int, int, int, int]:
    """
    @func: 将通过控件或者坐标指定的起始和结束位置统一转换为屏幕绝对坐标位置
    @param start: 起始位置，可以为控件或者坐标
    @param end: 结束位置，可以为控件或者坐标
    @param area: 限制区域，设置后坐标类型的start和end将被视为相对该区域的坐标
    @return: 返回计算出的起始坐标和结束坐标start_x, start_y, end_x, end_y
    """
    start_type = type(start)
    end_type = type(end)
    base_x = 0
    base_y = 0
    bounds = None
    # 计算限制区域
    if area is not None:
        component = _convert_to_uicomponent(driver, area)
        bounds = component.getBounds()
        base_x = bounds.leftX
        base_y = bounds.topY
    # 计算起始坐标
    if start_type == tuple:
        start_x, start_y = start
    elif isinstance(start, ISelector) or isinstance(start, IUiComponent):
        point = _convert_to_uicomponent(driver, start).getBoundsCenter()
        start_x, start_y = point.X, point.Y
    else:
        raise HypiumParamUiTargetError(start_type)
    # 计算结束坐标
    if end_type == tuple:
        end_x, end_y = end
    elif isinstance(end, ISelector) or isinstance(end, IUiComponent):
        point = _convert_to_uicomponent(driver, end).getBoundsCenter()
        end_x, end_y = point.X, point.Y
    else:
        raise HypiumParamUiTargetError(end_type)

    if utils.is_scale((start_x, start_y)):
        if bounds is None:
            bounds = driver.display_size
        start_x, start_y = utils.scale_to_position((start_x, start_y), bounds)
    else:
        # 计算包含限制区域的坐标
        start_x, start_y = base_x + start_x, base_y + start_y

    if utils.is_scale((end_x, end_y)):
        if bounds is None:
            bounds = driver.display_size
        end_x, end_y = utils.scale_to_position((end_x, end_y), bounds)
    else:
        end_x, end_y = end_x + base_x, end_y + base_y
    return int(start_x), int(start_y), int(end_x), int(end_y)


def _slide_by_cmd(driver: ArkUiDriver, start_x, start_y, end_x, end_y, slide_time, mode="slide", press_time=1):
    # api8 兼容实现

    if mode == "slide":
        cmd = "uinput -T -m %d %d %d %d %d" % (start_x, start_y, end_x, end_y, int(slide_time * 1000))
    else:
        cmd = "uinput -T -g %d %d %d %d %d %d" % (start_x, start_y, end_x, end_y, int(press_time * 1000),
                                                  int(slide_time * 1000))

    # 执行shell
    echo = driver.get_shell_instance().execute(cmd)
    if not utils.is_cmd_success(echo):
        raise HypiumOperationFailError(echo)


def _slide(driver: ArkUiDriver, start_x, start_y, end_x, end_y, slide_time, mode="slide", press_time: float = 1.5):
    """
    @func 执行滑动和拖拽操作
    """
    # 计算滑动操作坐标
    start_x, start_y = int(start_x), int(start_y)
    end_x, end_y = int(end_x), int(end_y)
    distance = abs(end_y - start_y + end_x - start_x)
    speed = int(distance / slide_time * 0.9)
    if speed <= 0:
        speed = 1
    if mode == "slide":
        driver.swipe(start_x, start_y, end_x, end_y, speed)
    else:
        if press_time > 1.5:
            driver.dragBetween(Point(start_x, start_y), Point(end_x, end_y), speed, int(press_time * 1000))
        else:
            driver.drag(start_x, start_y, end_x, end_y, speed)


def _is_scale(pos):
    """检查坐标值是否为比例"""
    for item in pos:
        if 0 <= item <= 1:
            return True
        else:
            return False


def _convert_to_absolute_position(driver: ArkUiDriver, pos, area_size=None) -> (int, int):
    """检查是否为比例坐标，如果是则进行转换"""
    if not _is_scale(pos):
        return int(pos[0]), int(pos[1])
    if area_size is None:
        point = driver.getDisplaySize()
        width, height = point.X, point.Y
    else:
        width, height = area_size
    return int(pos[0] * width), int(pos[1] * height)


def _generate_absolute_path(device_path: str, device_path_type: str = "root") -> str:
    """生成绝对路径"""
    path_prefix = {
        "root": "",
        "tmp": "/data/local/tmp"
    }
    if device_path_type not in path_prefix.keys():
        raise HypiumNotSupportError("Invalid device path type: %s" % device_path_type)
    return path_prefix[device_path_type] + device_path


def _search_pkg_name(focus_window, mission_info):
    # 获取前台所有应用
    pkg_names = re.findall(r"Mission ID #(\d+)\s+mission name #\[(.*?)\]", mission_info)
    if focus_window and pkg_names:
        for mission in pkg_names:
            mission_id = mission[0]
            if focus_window == mission_id:
                mission_name = mission[1]
                pkg_name = mission_name.split(":")[0].replace("#", "")
                ability_name = mission_name.split(":")[-1]
                result = (pkg_name, ability_name)
                return result
    # 未找到对应应用
    return None


def _ohos_get_current_app_by_cmd(driver: ArkUiDriver):
    echo = driver.execute_shell_command("hidumper -s WindowManagerService -a '-a'")
    # 获取当前前台应用焦点id
    focus_window = re.search(r"Focus window: (\d+)", echo)
    if focus_window:
        focus_window = focus_window.group(1)
    mission_echo = driver.execute_shell_command("hidumper -s AbilityManagerService -a -l")
    result = _search_pkg_name(focus_window, mission_echo)
    if result is None:
        result = _search_pkg_name(focus_window, echo)
    if result:
        return result
    else:
        return None, None


class CompatibleInterfaceMixIn:
    """@inner兼容性接口"""

    def log_debug(self, msg):
        warnings.warn("use driver.log.debug insteaded", DeprecationWarning)
        self.log.debug(msg)

    def log_info(self, msg):
        warnings.warn("use driver.log.info insteaded", DeprecationWarning)
        self.log.info(msg)

    def log_warning(self, msg):
        warnings.warn("use driver.log.warning insteaded", DeprecationWarning)
        self.log.warning(msg)

    def log_error(self, msg):
        warnings.warn("use driver.log.error insteaded", DeprecationWarning)
        self.log.error(msg)

    def execute_shell_command(self, cmd, timeout=300):
        warnings.warn("use driver.shell insteaded", DeprecationWarning)
        return self.shell(cmd, timeout)

    def execute_connector_command(self, cmd, timeout=300):
        warnings.warn("use driver.hdc insteaded", DeprecationWarning)
        return self.hdc(cmd, timeout)

    def get_component_pos(self, comp):
        bounds = self.get_component_bound(comp)
        if bounds:
            return bounds.get_center()
        else:
            return None

    def to_absolute_position(self, x, y):
        return self.to_abs_pos(x, y)

    @property
    def device_type(self):
        return self.get_device_type()

    @property
    def sn(self):
        return self.device_sn

    @property
    def os_type(self):
        return self.get_os_type()

    @property
    def ScreenLock(self):
        class FakeModuleScreenLock:
            def is_locked(self):
                return False

        return FakeModuleScreenLock()


def raw_click_compatible(func: T) -> T:
    @wraps(func)
    def wrapper(obj, *args, **kwargs):
        if len(args) == 2:
            x, y = args
            if isinstance(x, int) and isinstance(y, int):
                return obj.driver.click(x, y)
            else:
                return func(obj, *args, **kwargs)
        else:
            return func(obj, *args, **kwargs)

    return wrapper


class OHOSDriver(OSAwBase, IUiDriver, CompatibleInterfaceMixIn):
    """
    @inner hypium基础UI测试驱动模块OHOS系统实现, 提供基础的UI操作/检查能力和应用测试相关的能力
    """

    def close_display(self):
        echo = self.driver.execute_shell_command("power-shell suspend", timeout=10)
        self.log.debug(echo)

    def unlock(self):
        w, h = self.get_display_size()
        self.wake_up_display()
        time.sleep(1)
        if not self.is_display_locked():
            return
        if self.device_type == DeviceType.TWO_IN_ONE:
            self.driver.triggerKey(KeyCode.ENTER)
        else:
            start = int(0.5 * w), int(0.99 * h)
            end = int(0.5 * w), int(0.7 * h)
            self.slide(start, end, slide_time=0.1)

    def set_sleep_time(self, sleep_time: float):
        if not self.is_display_on():
            self.wake_up_display()
        echo = self.driver.execute_shell_command("power-shell timeout -o %s" % (int(sleep_time * 1000)))
        self.log.debug(echo)

    def restore_sleep_time(self):
        echo = self.driver.execute_shell_command("power-shell timeout -r")
        self.log.debug(echo)

    def is_display_on(self):
        echo = self.driver.execute_shell_command("hidumper -s PowerManagerService -a '-a'")
        return "Current State: AWAKE" in echo

    def is_display_locked(self):
        echo = self.driver.execute_shell_command("hidumper -s ScreenlockService -a -all")
        for line in echo.split():
            if "screenLocked" not in line:
                continue
            if "false" in line:
                return False
            else:
                return True
        return not self.is_display_on()

    @property
    def log(self):
        """
        @func 日志模块
        """
        return self._device.log

    def set_implicit_wait_time(self, wait_time: float):
        """
        @func:    设置操作控件类的接口在控件未出现时等待的超时时间
        @param:   wait_time: 操作控件类的接口在控件未出现时等待的时间
        """
        setattr(self.driver, "implicit_wait_time", wait_time)

    def get_implicit_wait_time(self) -> float:
        return getattr(self.driver, "implicit_wait_time", 10)

    def get_device_type(self) -> str:
        return self.shell("param get const.product.devicetype").strip()

    def get_os_type(self) -> str:
        return OSType.OHOS

    def close(self):
        """
        @func 关闭驱动, 断开与设备的连接并清理连接资源。
              仅当使用UiDriver.connect方式创建设备驱动时需要在驱动对象不再使用时调用
              如果在Hypium框架用例中创建驱动则无需主动调用
        @example:
              # 通过UiDriver.connect方式连接
              driver = UiDriver.connect()
              # 调用driver执行操作
              driver.go_home()
              # 不再使用driver时关闭
              driver.close()
        """
        self._device.reset()

    def __init__(self, device, agent_mode: str = 'auto', **kwargs):
        if device is None:
            raise HypiumParamError(msg="Device object is None, please check if correct device is connected")
        self.driver: ArkUiDriver = None
        self._set_agent_mode(device, agent_mode)
        if not isinstance(device, ArkUiDriver):
            driver = ArkUiDriver.create(device)
        else:
            driver = device
        if driver is None:
            raise HypiumOperationFailError("Fail to create UiDriver, please check device uitest status")
        self._event_manager = EventManager()
        super().__init__(driver)

    def __getattr__(self, item):
        result = None
        if item != "driver":
            result = getattr(self.driver, item, None)
        if result is None:
            raise AttributeError("OHOSDriver has not attribute %s" % item)
        return result

    def _set_agent_mode(self, device, agent_mode: str):
        device_helper.set_device_agent_mode(device, "bin")

    def add_hook(self, hook_type, hook_id, callback):
        self._event_manager.subscribe(hook_type, hook_id, callback)

    def remove_hook(self, hook_type, hook_id):
        self._event_manager.unsubscribe(hook_type, hook_id)

    def remove_all_hooks(self, hook_type):
        self._event_manager.unsubscribe_all(hook_type)

    @record_action
    @raw_click_compatible
    def click(self, target: Union[ISelector, IUiComponent, tuple], offset=None):
        x, y = self._convert_to_abs_pos(target, offset)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.click(x, y)

    def double_click(self, target: Union[ISelector, IUiComponent, tuple], offset=None):
        x, y = self._convert_to_abs_pos(target, offset)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.doubleClick(x, y)

    def long_click(self, target: Union[ISelector, IUiComponent, tuple], press_time: float = 2, offset=None):
        x, y = self._convert_to_abs_pos(target, offset)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.shell(f"uinput -T -d {x} {y} -i {int(press_time * 1000)} -u {x} {y}")

    def hdc(self, cmd, timeout: float = 60) -> str:
        """
        @func 执行hdc命令
        @param cmd: 执行的hdc命令
        @param timeout: 超时时间, 单位秒
        @return 命令执行后的回显内容
        @example # 执行hdc命令list targets
                 echo = driver.hdc("list targets")
                 # 执行hdc命令hilog, 设置30秒超时
                 echo = driver.hdc("hilog", timeout = 30)
        """
        return self._device.connector_command(cmd, timeout=int(timeout * 1000))

    def shell(self, cmd: str, timeout: float = 60) -> str:
        """
        @func 在设备端shell中执行命令
        @param cmd: 执行的shell命令
        @param timeout: 超时时间, 单位秒
        @return 命令执行后的回显内容
        @example # 在设备shell中执行命令ls -l
                 echo = driver.shell("ls -l")
                 # 在设备shell中执行命令top, 设置10秒超时时间
                 echo = driver.shell("top", timeout=10)
        """
        return self._device.execute_shell_command(cmd, timeout=int(timeout * 1000))

    def pull_file(self, device_path: str, local_path: str = None, timeout: int = 60):
        """
        @func:     从设备端的传输文件到pc端
        @param:    local_path: PC侧保存文件的路径
        @param:    device_path: 设备侧保存文件的路径
        @param:   timeout: 拉取文件超时时间, 默认60秒
        @example: # 从设备中拉取文件"/data/local/tmp/test.log"保存到pc端的test.log
                  driver.pull_file("/data/local/tmp/test.log", "test.log")
        """
        driver = self.driver
        device_path = _generate_absolute_path(device_path)
        local_path = os.path.abspath(local_path)
        cmd = 'file recv "%s" "%s"' % (device_path, local_path)
        echo = driver.exectue_connector_command(cmd, timeout=timeout)
        if not utils.is_cmd_success(echo):
            raise HypiumOperationFailError(echo)

    def push_file(self, local_path: str, device_path: str, timeout: int = 60):
        """
        @func:   从pc端传输文件到设备端
        @param:  local_path: PC侧文件的路径
        @param:  device_path: 设备侧文件的路径
        @param:  device_path_type: 同pull_file
        @param:  timeout: 推送文件超时时间
        """
        driver = self.driver
        local_path = os.path.abspath(local_path)
        device_path = _generate_absolute_path(device_path)
        cmd = 'file send "%s" "%s"' % (local_path, device_path)
        echo = driver.exectue_connector_command(cmd, timeout=timeout)
        if not utils.is_cmd_success(echo):
            raise HypiumOperationFailError(echo)

    def has_file(self, file_path: str):
        """
        @func   查询设备中是否有存在路径为file_path的文件
        @param   file_path: 需要检查的设备端文件路径
        @example # 查询设备端是否存在文件/data/local/tmp/test_file.txt
                 driver.Storage.has_file("/data/local/tmp/test_file.txt")
        """
        driver = self.driver
        shell = driver.get_shell_instance()
        filepath = file_path.strip()
        if len(filepath) == 0:
            return False
        result = shell.execute("ls " + filepath)
        if "No such file" in result:
            return False
        else:
            return True

    def wait(self, wait_time: float):
        """
        @func: 等待wait_time秒
        @param: wait_time: 等待秒数
        """
        time.sleep(wait_time)

    def start_app(self, package_name: str, page_name: str = None, params: str = "", wait_time: float = 1, **kwargs):
        driver = self.driver
        org_page_name = page_name
        if page_name is None:
            main_ability_info = app_manager.get_main_ability(driver, package_name)
            if main_ability_info is None:
                raise ValueError(f"Fail to get main ability of [{package_name}], please specify one")
            ability_name = main_ability_info.get("name")
        else:
            ability_name = page_name
        Tracker.event(TrackerEvent.APP_INFO.id, event_name=TrackerEvent.APP_INFO.name, extraData={
            "bundle_name": package_name
        })
        cmd = f"aa start -b {package_name} -a {ability_name} {params}"
        echo = driver.execute_shell_command(cmd)
        if utils.is_cmd_success(echo):
            time.sleep(wait_time)
        else:
            msg = ""
            if org_page_name is None:
                msg = f"start default mainAbility [{ability_name}] failed. "
                self.driver.log_warning(msg)
            raise HypiumOperationFailError(msg + echo)

    def stop_app(self, package_name: str, wait_time: float = 0.5):
        """
        @func      停止指定的应用
        @param     package_name: 应用程序包名
        @param     wait_time: 停止app后延时等待的时间, 单位为秒
        @example   # 停止com.ohos.settings
                   driver.stop_app("com.ohos.settings")
        """
        driver = self.driver
        device = driver._device
        # 默认启动MainAbility
        bundle_name = package_name
        cmd = "aa force-stop %s" % bundle_name
        shell = driver.get_shell_instance()
        echo = shell.execute(cmd)
        if utils.is_cmd_success(echo):
            time.sleep(wait_time)
        else:
            raise HypiumOperationFailError(echo + f"请检查 {package_name} 是否已安装")

    def has_app(self, package_name: str) -> bool:
        """
        @func 查询是否安装指定包名的app
        @param package_name: 需要检查的应用程序包名
        """
        echo = self.driver.execute_shell_command("bm dump -a | grep %s" % package_name)
        if package_name not in echo:
            return False
        else:
            return True

    def current_app(self) -> (str, str):
        """
        @func 获取当前前台焦点的app信息
        @return app包名和页面名称, 例如('com.huawei.hmos.settings', 'MainAbility'),
                如果读取失败，或者位于桌面则返回(None, None)
        @example: package_name, page_name = driver.current_app()
        """
        pkg_name, ability_name = _ohos_get_current_app_by_cmd(self.driver)
        return pkg_name, ability_name

    def install_app(self, package_path: str, options: str = "", **kwargs):
        """
        @func 安装app
        @param package_path: PC端保存的安装包路径
        @param options: 传递给install命令的额外参数
        @example  # 安装路径为D:\test.hap的安装包到手机
                  driver.AppManager.install_app(r"D:\test.hap")
                  # 替换安装路径为D:\test.hap的安装包到手机(增加-r参数指定替换安装)
                  driver.AppManager.install_app(r"D:\test.hap", "-r")
        """
        driver = self.driver
        options = options.split()
        cmd_list = ["install"]
        cmd_list.extend(options)
        cmd_list.append(package_path)
        echo = driver.exectue_connector_command(cmd_list)
        driver.log_info(echo)
        if not utils.is_cmd_success(echo):
            raise HypiumOperationFailError(echo)

    def uninstall_app(self, package_name: str, **kwargs):
        """
        @func 卸载App
        @param package_name: 需要卸载的app包名
        @example driver.uninstall_app(driver, "com.ohos.devicetest")
        """
        driver = self.driver
        echo = driver.execute_shell_command(f'bm uninstall -n {package_name}')
        if not utils.is_cmd_success(echo):
            raise HypiumOperationFailError(echo)

    def clear_app_data(self, package_name: str):
        """
        @func 清除app的数据
        @param package_name: app包名，对应Openharmony中的bundle name
        @example # 清除包名为com.tencent.mm的应用的所有数据
                 driver.clear_app_data("com.tencent.mm")
        """
        driver = self.driver
        cmd = f"bm clean -n {package_name} -d"
        echo = driver.execute_shell_command(cmd)
        if not utils.is_cmd_success(echo):
            self.log.warning("Only support clean cache in user device")
            cmd = f"bm clean -n {package_name} -c"
            echo = driver.execute_shell_command(cmd)
            if not utils.is_cmd_success(echo):
                raise HypiumOperationFailError(f"Fail to clean cache for {package_name}")

    def wake_up_display(self):
        """
        @func 唤醒屏幕
        @example # 唤醒屏幕
                 driver.wake_up_display()
        """
        self.driver.execute_shell_command("power-shell wakeup")

    def get_display_rotation(self) -> DisplayRotation:
        """
        @func: 获取当前设备的屏幕显示方向
        @example # 获取当前设备的屏幕显示方向
             driver.get_display_rotation()
        """
        return self.driver.getDisplayRotation()

    def set_display_rotation(self, rotation: DisplayRotation):
        """
        @func: 将设备的屏幕显示方向设置为指定的显示方向
        @param rotation: left-左横屏/right-右横屏/natural-竖屏/portrait-倒竖屏
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return self.driver.setDisplayRotation(rotation)

    def set_display_rotation_enabled(self, enabled: bool):
        """
        @func: 启用/禁用设备旋转屏幕的功能
        @param enabled: 能否旋转屏幕的标识
        @example # 获取当前设备的屏幕显示方向
             driver.set_display_rotation_enabled(True)
             driver.set_display_rotation_enabled(False)
        """
        return self.driver.setDisplayRotationEnabled(enabled)

    def drag(self, start: Union[ISelector, tuple, IUiComponent], end: Union[ISelector, tuple, IUiComponent],
             area: Union[ISelector, IUiComponent] = None, press_time: float = 1.5, drag_time: float = 1, speed: int = None):
        """
        @func:       根据指定的起始和结束位置执行拖拽操作，起始和结束的位置可以为控件或者屏幕坐标
        @param:      start: 拖拽起始位置，可以为控件BY.text(“滑块”)或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      end: 拖拽结束位置，可以为控件BY.text(“最大值”)或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      area: 拖拽操作区域，可以为控件BY.text("画布"), 或者使用find_component找到的控件对象。
                           目前仅在start或者end为坐标时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域
                           的相对位置坐标。
        @param:      press_time: 拖拽操作开始时，长按的时间, 默认为1.5s
        @param:      drag_time: 拖动的时间， 默认为1s(整个拖拽操作总时间 = press_time + drag_time)
        @example:    # 拖拽文本为"文件.txt"的控件到文本为"上传文件"的控件
                     driver.drag(BY.text("文件.txt"), BY.text("上传文件"))
                     # 拖拽id为"start_bar"的控件到坐标(100, 200)的位置, 拖拽时间为2秒
                     driver.drag(BY.key("start_bar"), (100, 200), drag_time=2)
                     # 在id为"Canvas"的控件上从相对位置(10, 20)拖拽到(100, 200)
                     driver.drag((10, 20), (100, 200), area = BY.id("Canvas"))
                     # 在滑动条上从相对位置(10, 10)拖拽到(10, 200)
                     driver.drag((10, 10), (10, 200), area=BY.type("Slider"))
        """
        # 计算拖拽操作坐标
        driver = self.driver
        start_x, start_y, end_x, end_y = _generate_drag_position(driver, start, end, area)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                         {"operate_type": "drag", "start_point": (start_x, start_y), "end_point": (end_x, end_y)})
        if speed is not None:
            if speed <= 0 or speed > 40000:
                raise ValueError("speed must in the range (0,40000], get %s" % speed)
            else:
                distance_pixels = (end_x - start_x) ** 2 + (end_y - start_y) ** 2
                distance_pixels = int(math.sqrt(distance_pixels))
                drag_time = distance_pixels / speed
        _slide(driver, start_x, start_y, end_x, end_y, drag_time, mode="drag", press_time=press_time)

    def touch(self, target: Union[ISelector, IUiComponent, tuple], mode: str = "normal",
              scroll_target: Union[ISelector, IUiComponent] = None, wait_time: float = 0.1, offset: tuple = None):
        """
        @func:    根据选定的控件或者坐标位置执行点击操作
        @param:   target: 需要点击的目标，可以为控件(通过ISelector类指定)或者屏幕坐标(通过tuple类型指定，
                         例如(100, 200)， 其中100为x轴坐标，200为y轴坐标), 或者使用find_component找到的控件对象
        @param:   mode: 点击模式，目前支持:
                       "normal" 点击
                       "long" 长按（长按后放开）
                       "double" 双击
        @param:   scroll_target: 指定可滚动的控件，在该控件中滚动搜索指定的目标控件target。仅在
                                target为`ISelector`对象时有效
        @param:   wait_time: 点击后等待响应的时间，默认0.1s
        @example: # 点击文本为"hello"的控件
                  driver.touch(BY.text("hello"))
                  # 点击(100, 200)的位置
                  driver.touch((100, 200))
                  # 点击比例坐标为(0.8, 0.9)的位置
                  driver.touch((0.8, 0.9))
                  # 双击确认按钮(控件文本为"确认", 类型为"Button")
                  driver.touch(BY.text("确认").type("Button"), mode=UiParam.DOUBLE)
                  # 在类型为Scroll的控件上滑动查找文本为"退出"的控件并点击
                  driver.touch(BY.text("退出"), scroll_target=BY.type("Scroll"))
                  # 长按相对坐标为(0.8, 0.9)的位置
                  driver.touch((0.8, 0.9))
        """
        driver = self.driver
        target_type = type(target)
        if isinstance(target, tuple):
            x, y = self._convert_to_abs_pos(target, offset)
            self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                             {"operate_type": "click", "point": (x, y)})
            if mode == UiParam.NORMAL:
                driver.click(x, y)
            elif mode == UiParam.LONG:
                driver.longClick(x, y)
            elif mode == UiParam.DOUBLE:
                driver.doubleClick(x, y)
            else:
                raise HypiumParamTouchModeError(mode)
        elif isinstance(target, ISelector) or isinstance(target, IUiComponent):
            # find component
            if scroll_target is not None:
                scroll_component = _convert_to_uicomponent(driver, scroll_target)
                self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
                target_component = scroll_component.scrollSearch(target)
            else:
                target_component = _convert_to_uicomponent(driver, target)
            # do click
            component_rect = None
            try:
                if len(self._event_manager.subscribers) > 0:
                    component_rect = target_component.getBounds()
                    pos = component_rect.get_center()
                    self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                                     {"operate_type": "click", "point": (pos[0], pos[1])})
            except Exception as e:
                self.log.warning("Fail to get component position info: %s" % repr(e))

            if offset:
                # 处理传入了offset的场景
                if not component_rect:
                    component_rect = target_component.getBounds()
                x, y = self._convert_to_abs_pos(component_rect, offset)
                if mode == UiParam.NORMAL:
                    self.driver.click(x, y)
                elif mode == UiParam.LONG:
                    self.driver.longClick(x, y)
                elif mode == UiParam.DOUBLE:
                    self.driver.doubleClick(x, y)
            else:
                if mode == UiParam.NORMAL:
                    target_component.click()
                elif mode == UiParam.LONG:
                    target_component.longClick()
                elif mode == UiParam.DOUBLE:
                    target_component.doubleClick()
                else:
                    raise HypiumParamTouchModeError(mode)
        else:
            raise HypiumParamUiTargetError(target_type)
        time.sleep(wait_time)

    @record_action
    def _get_image_pos(self, image_path_pc: str, similarity: float = 0.95, **kwargs):
        image_abs_path = os.path.abspath(image_path_pc)
        screen_image_path = self.capture_screen(os.path.join(utils.get_tmp_dir(), "devicetest.jpeg"))
        max_similarity, pos = cv.match_image_location(screen_image_path, image_abs_path)
        if max_similarity >= similarity:
            return pos
        self.log.debug(f"template match similarity is {max_similarity}")
        if "area_check" not in kwargs:
            kwargs["area_check"] = False
        result = CVBasic.find_image(image_abs_path, screen_image_path, **kwargs)
        if result is None:
            return result
        return result.get_center()

    def find_image(self, image_path_pc: str, mode="sift", **kwargs) -> Rect:
        """
        @func 在屏幕上查找指定图片的位置
        @param image_path_pc: 模板图片的路径
        @param mode: 图片匹配模式, 支持template和sift, 图片分辨率/旋转变化对sift模式影响相对较小，但sift模式难以处理缺少较复杂图案
                     的纯色，无线条图片
        @param kwargs: 其他配置参数
               min_match_point: sift模式支持, 最少匹配特征点数, 值越大匹配越严格, 默认为16
               similarity: template模式支持，图片最小相似度
        @return 图片在屏幕上的矩形区域位置, 如果没有找到则返回None
        @example: # 在屏幕上查找icon.png的位置
                  bounds = driver.find_image("icon.png")
                  # 点击图片中心坐标
                  driver.touch(bounds.get_center())
        """
        image_abs_path = os.path.abspath(image_path_pc)
        screen_image_path = self.capture_screen(os.path.join(utils.get_tmp_dir(), "devicetest.jpeg"))
        result = CVBasic.find_image(image_abs_path, screen_image_path, mode, **kwargs)
        if result is None:
            return result
        return result

    def touch_image(self, image_path_pc: str, mode: str = "normal", similarity: float = 0.95,
                    wait_time: int = 0.1, **kwargs):
        """
        @func:    在屏幕上显示内容同图片image_path_pc内容相同的位置执行点击操作， 注意图片的分辨率必须同屏幕上目标显示区域的分辨率相同才能
                  正常匹配，如果图片被缩放/旋转将无法正常匹配到正确的位置。
        @param:   image_path_pc: 需要点击的图像的存储路径(图片存储在PC端)
        @param:   mode: 点击模式，目前支持:
                       "normal" 点击
                       “long” 长按（长按后放开）
                       ”double“ 双击
        @param:   wait_time: 点击后等待响应的时间，默认0.1s
        @param:   kwargs: 其他配置参数
                  min_match_point: 最少匹配特征点数, 值越大匹配越严格, 默认为16个(同similarity参数独立，用于控制另外一种算法匹配图片)
        @example: # 使用图片的方式点击屏幕上显示内容为button.jpeg的位置
                  driver.touch_image("button.jpeg")
                  # 双击图片button.jpeg的位置
                  driver.touch_image("button.jpeg", mode=UiParam.DOUBLE)
                  # 长按图片button.jpeg的位置
                  driver.touch_image("button.jpeg", mode=UiParam.LONG)
                  # 点击图片button.jpeg的位置, 相似度设置为0.8
                  driver.touch_image("button.jpeg", similarity=0.8)
                  # 点击图片button.jpeg的位置, 特征点最少匹配16个
                  driver.touch_image("button.jpeg", min_match_point=16)
        """
        pos = self._get_image_pos(image_path_pc, similarity, **kwargs)
        if pos is None:
            raise HypiumOperationFailError("touch image failed, No such image on screen")
        self.touch(pos, mode, wait_time=wait_time)

    def switch_component_status(self, component: Union[ISelector, IUiComponent], checked: bool):
        """
        @func 切换带有状态的控件的状态，例如单选框选中与取消选中
        @param component: 操作的目标控件
        @param checked: 设置控件的check状态
        @example: # 切换id为"confirm_checkbox"的控件为选中状态
                  driver.switch_component_status(BY.key("confirm_checkbox"), checked=True)
                  # 切换id为"confirm_checkbox"的控件为未选中状态
                  driver.switch_component_status(BY.key("confirm_checkbox"), checked=False)
        """
        driver = self.driver
        component = _convert_to_uicomponent(driver, component)
        if component.isChecked() != checked:
            self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
            component.click()

    def _convert_key_code(self, key_code: Union[KeyCode, int]) -> int:
        if isinstance(key_code, KeyCode):
            return key_code.value
        else:
            return key_code

    def press_combination_key(self, key1: Union[KeyCode, int], key2: Union[KeyCode, int],
                              key3: Union[KeyCode, int] = None):
        """
        @func 按下组合键, 支持2键或者3键组合
        @param key1: 组合键第一个按键
        @param key2: 组合键第二个按键
        @param key3: 组合键第三个按键(HMOS不支持三键组合, 第三个按键不会生效)
        @example # 按下音量下键和电源键的组合键
                 driver.press_combination_key(KeyCode.VOLUME_DOWN, KeyCode.POWER)
                 # 同时按下ctrl, shift和F键
                 driver.press_combination_key(KeyCode.CTRL_LEFT, KeyCode.SHIFT_LEFT, KeyCode.F)
        """
        driver = self.driver
        keys = []
        for item in (key1, key2, key3):
            if item is not None:
                keys.append(self._convert_key_code(item))
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return driver.triggerCombineKeys(*keys)

    def press_key(self, key_code: Union[KeyCode, int], key_code2: Union[KeyCode, int] = None,
                  mode="normal"):
        """
        @func 按下指定按键(按组合键请使用press_combination_key)
        @param key_code: 需要按下的按键编码
        @param key_code2: 需要按下的按键编码
        @param mode: 按键模式, 仅在进行单个按键时支持，支持:
                     UiParam.NORMAL 默认, 按一次
                     UiParam.LONG 长按
                     UiParam.DOUBLE 双击
        @example # 按下电源键
                 driver.press_key(KeyCode.POWER)
                 # 长按电源键
                 driver.press_key(KeyCode.POWER, mode=UiParam.LONG)
                 # 按下音量下键
                 driver.press_key(KeyCode.VOLUME_DOWN)
        """
        driver = self.driver
        shell = driver.get_shell_instance()
        key_code, key_code2 = self._convert_key_code(key_code), self._convert_key_code(key_code2)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        if key_code2 is None:
            if mode == UiParam.NORMAL:
                driver.triggerKey(key_code)
            elif mode == UiParam.LONG:
                shell.execute("uinput -K -l %s" % key_code)
            elif mode == UiParam.DOUBLE:
                shell.execute("uinput -K -d %s -u %s -i 200 -d %s -u %s" % (key_code, key_code, key_code, key_code))
            else:
                raise HypiumParamTouchModeError(mode)
        else:
            driver.triggerCombineKeys(key_code, key_code2)

    def press_home(self):
        """
        @func 按下HOME键
        @example: # 按下home键
                  driver.press_home()
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.pressHome()
        time.sleep(1)

    def go_home(self):
        """
        @func 返回桌面(不关心返回桌面的方式，自动决定最稳定的返回桌面方式)
        @example: # 返回桌面
                  driver.go_home()
        """
        if DeviceType.is_tablet_category(self.get_device_type()):
            pkg, ability = self.current_app()
            if pkg is not None:
                self.press_combination_key(KeyCode.META_LEFT, KeyCode.D)
        else:
            self.press_home()

    def go_back(self):
        """
        @func 返回上一级(不关心返回桌面的方式，自动决定最稳定的返回方式)
        @example: # 返回桌面
                  driver.go_back()
        """
        if DeviceType.is_tablet_category(self.get_device_type()):
            self.press_back()
        else:
            self.swipe_to_back()

    def press_power(self):
        """
        @func 按下电源键
        @example: # 按下电源键
                  driver.press_power()
        """
        driver = self.driver
        keycode = KeyCode.POWER
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        driver.triggerKey(keycode)

    def get_component_bound(self, component: Union[ISelector, IUiComponent]) -> Rect:
        """
        @func 获取通过ISelector类指定的控件的边界坐标
        @return: 返回控件边界坐标的Rect对象，如果没找到控件则返回None
        @example # 获取text为按钮的控件的边框位置
                 bounds = driver.get_component_bound(BY.text(“按钮”))
                 # 获取控件对象的边框位置
                 component = driver.find_component(BY.text("按钮"))
                 bounds = driver.get_component_bound(component)
        """
        driver = self.driver
        component = _convert_to_uicomponent(driver, component)
        if component is None:
            return None
        else:
            return component.getBounds()

    def press_back(self):
        """
        @func 按下返回键
        @example: # 按下返回键
                  driver.press_back()
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.pressBack()

    def slide(self, start: Union[By, tuple], end: Union[By, tuple],
              area: Union[By, UiComponent] = None, slide_time: float = DEFAULT_SLIDE_TIME):
        """
        @func:       根据指定的起始和结束位置执行滑动操作，起始和结束的位置可以为控件或者屏幕坐标。该接口用于执行较为精准的滑动操作。
        @param:      start: 滑动起始位置，可以为控件BY.text(“滑块”)或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      end: 滑动结束位置，可以为控件BY.text(“最大值”)或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      area: 滑动操作区域，可以为控件BY.text("画布")。目前仅在start或者end为坐标
                           时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域
                           的相对位置坐标。
        @param:      slide_time: 滑动操作总时间，单位秒
        @example:    # 从类型为Slider的控件滑动到文本为最大的控件
                     driver.slide(BY.type("Slider"), BY.text("最大"))
                     # 从坐标100, 200滑动到300，400
                     driver.slide((100, 200), (300, 400))
                     # 从坐标100, 200滑动到300，400, 滑动时间为3秒
                     driver.slide((100, 200), (300, 400), slide_time=3)
                     # 在类型为Slider的控件上从(0, 0)滑动到(100, 0)
                     driver.slide((0, 0), (100, 0), area = BY.type("Slider))
        """
        # 计算滑动操作坐标
        driver = self.driver
        start_x, start_y, end_x, end_y = _generate_drag_position(driver, start, end, area)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                         {"operate_type": "swipe", "start_point": (start_x, start_y),
                                          "end_point": (end_x, end_y)})
        _slide(driver, start_x, start_y, end_x, end_y, slide_time)

    def _generate_center_swipe_start_point(self, side: str, center, direction, distance):
        center_x, center_y = center
        step = int(distance / 2)
        # 转换中心点
        if side == UiParam.TOP:
            center_y = int(center_y * 0.3)
        elif side == UiParam.BOTTOM:
            center_y = int(center_y * 1.8)
        elif side == UiParam.LEFT:
            center_x = int(center_x * 0.3)
        elif side == UiParam.RIGHT:
            center_x = int(center_x * 1.8)

        # 计算起始点
        if direction == UiParam.LEFT:
            start_x = center_x + step
            start_y = center_y
        elif direction == UiParam.RIGHT:
            start_x = center_x - step
            start_y = center_y
        elif direction == UiParam.UP:
            start_x = center_x
            start_y = center_y + step
        elif direction == UiParam.DOWN:
            start_x = center_x
            start_y = center_y - step
        else:
            raise HypiumParamDirectionError(direction)
        return start_x, start_y

    def _generate_swipe_end_point(self, start_point, direction, distance):
        start_x, start_y = start_point
        if direction == UiParam.LEFT:
            end_x = start_x - distance
            end_y = start_y
        elif direction == UiParam.RIGHT:
            end_x = start_x + distance
            end_y = start_y
        elif direction == UiParam.UP:
            end_x = start_x
            end_y = start_y - distance
        elif direction == UiParam.DOWN:
            end_x = start_x
            end_y = start_y + distance
        else:
            raise HypiumParamDirectionError(direction)
        return end_x, end_y

    def _generate_absolute_distance(self, direction, distance_scale, area_width, area_height) -> int:
        if direction in (UiParam.LEFT, UiParam.RIGHT):
            return int(area_width * distance_scale)
        elif direction in (UiParam.UP, UiParam.DOWN):
            return int(area_height * distance_scale)
        else:
            raise HypiumParamDirectionError(direction)

    def _scale_to_position(self, pos, area_size=None):
        if area_size is None:
            area_size = self.driver.getDisplaySize().to_tuple()
        width, height = area_size
        x, y = pos
        if 0 <= x <= 1 or 0 <= y <= 1:
            x = int(x * width)
            y = int(y * height)
        return x, y

    def _generate_swipe_position(self, direction: str, distance: int, side: str = None,
                                 start_point: tuple = None, area: Union[ISelector, IUiComponent] = None):

        # 获取滑动区域以及中心坐标
        driver = self.driver
        base_x = 0
        base_y = 0
        if distance < 0 or distance > 100:
            raise HypiumParamError(msg="distance [%s] is invalid, should be in range(0, 100)")
        if area is None:
            # 未指定区域时滑动区域为整个屏幕
            display_size = driver.getDisplaySize()
            center_x, center_y = display_size.X / 2, display_size.Y / 2
            len_x, len_y = display_size.X, display_size.Y
        else:
            # 指定区域时滑动区域为控件所在的区域
            area_type = type(area)
            if isinstance(area, ISelector) or isinstance(area, IUiComponent):
                component = _convert_to_uicomponent(driver, area)
                widget_bound = component.getBounds()
            elif isinstance(area, Rect):
                widget_bound = area
            else:
                raise HypiumParamAreaError(area_type)
            len_x = widget_bound.rightX - widget_bound.leftX
            len_y = widget_bound.bottomY - widget_bound.topY
            center_x = int((widget_bound.rightX + widget_bound.leftX) / 2)
            center_y = int((widget_bound.topY + widget_bound.bottomY) / 2)
            base_x = widget_bound.leftX
            base_y = widget_bound.topY
        distance = self._generate_absolute_distance(direction, distance / 100, len_x, len_y)
        if start_point is None:
            start_point = self._generate_center_swipe_start_point(side, (center_x, center_y), direction, distance)
        else:
            start_point = self._scale_to_position(start_point, (len_x, len_y))
            # add area offset if the start point is specified by user.
            start_point = (start_point[0] + base_x, start_point[1] + base_y)
        end_point = self._generate_swipe_end_point(start_point, direction, distance)
        x, y = start_point
        x1, y1 = end_point
        if x < 0 or y < 0 or x1 < 0 or y1 < 0:
            raise ValueError("Invalid param, start or end point is negative, start %s, end %s, " \
                             "please note that param [distance] is the percent of screen width/height)" %
                             (start_point, end_point))
        return (int(start_point[0]), int(start_point[1])), (int(end_point[0]), int(end_point[1]))

    def swipe(self, direction: str, distance: int = 60, area: Union[ISelector, IUiComponent] = None, side: str = None,
              start_point: tuple = None, swipe_time: float = 0.3, speed: int = None):
        """
        @func    在屏幕上或者指定区域area中执行朝向指定方向direction的滑动操作。该接口用于执行不太精准的滑动操作。
        @param   direction: 滑动方向，目前支持:
                            "LEFT" 左滑
                            "RIGHT" 右滑
                            "UP" 上滑
                            "DOWN" 下滑
        @param   distance: 相对滑动区域总长度的滑动距离，范围为1-100, 表示滑动长度为滑动区域总长度的1%到100%， 默认为60
        @param   area: 通过控件指定的滑动区域
        @param   side: 滑动位置， 指定滑动区域内部(屏幕内部)执行操作的大概位置，支持:
                        UiParam.LEFT 靠左区域
                        UiParam.RIGHT 靠右区域
                        UiParam.TOP 靠上区域
                        UiParam.BOTTOM 靠下区域
        @param   start_point: 滑动起始点, 默认为None, 表示在区域中间位置执行滑动操作, 可以传入滑动起始点坐标，支持使用(0.5, 0.5)
                              这样的比例相对坐标。当同时传入side和start_point的时候,
        @param   swipe_time: 滑动时间（s)， 默认0.3s
        @example    # 在屏幕上向上滑动, 距离40
                    driver.swipe(UiParam.UP, distance=40)
                    # 在屏幕上向右滑动, 滑动事件为0.1秒
                    driver.swipe(UiParam.RIGHT, swipe_time=0.1)
                    # 在屏幕起始点为比例坐标为(0.8, 0.8)的位置向上滑动，距离30
                    driver.swipe(UiParam.UP, 30, start_point=(0.8, 0.8))
                    # 在屏幕左边区域向下滑动， 距离30
                    driver.swipe(UiParam.DOWN, 30, side=UiParam.LEFT)
                    # 在屏幕右侧区域向上滑动，距离30
                    driver.swipe(UiParam.UP, side=UiParam.RIGHT)
                    # 在类型为Scroll的控件中向向滑动
                    driver.swipe(UiParam.UP, area=BY.type("Scroll"))
        """
        driver = self.driver
        start, end = self._generate_swipe_position(direction, distance, side, start_point, area)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                         {"operate_type": "swipe", "start_point": (start[0], start[1]), "end_point": (end[0], end[1])})
        if speed is not None:
            if speed <= 0 or speed > 40000:
                raise ValueError("speed must in the range (0,40000], get %s" % speed)
            else:
                start_x, start_y = start
                end_x, end_y = end
                distance_pixels = (end_x - start_x) ** 2 + (end_y - start_y) ** 2
                distance_pixels = int(math.sqrt(distance_pixels))
                swipe_time = distance_pixels / speed
        end_x, end_y = end
        end_x = max(0, end_x)
        end_y = max(0, end_y)
        end = (end_x, end_y)
        _slide(driver, *start, *end, swipe_time)

    def find_component(self, target: ISelector, scroll_target: ISelector = None) -> IUiComponent:
        """
        @func 根据BY指定的条件查找控件, 返回满足条件的第一个控件对象
        @param target: 使用ISelector对象描述的查找条件
        @param scroll_target: 滑动scroll_target控件, 搜索target
        @return 返回控件对象IUiComponent, 如果没有找到满足条件的控件，则返回None
        @example # 查找类型为button的第一个控件对象
                 component = driver.find_component(BY.type(“button”))
                 # 获取控件对象的文本
                 text = component.getText()
                 # 在类型为Scroll的控件上滚动查找文本为"拒绝"的控件
                 component = driver.find_component(BY.text("拒绝"), scroll_target=BY.type("Scroll"))
        """
        driver = self.driver
        if scroll_target is None:
            return driver.findComponent(target)
        if isinstance(scroll_target, ISelector):
            scroll_target = driver.findComponent(scroll_target)
            if scroll_target is None:
                return None
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return scroll_target.scrollSearch(target)

    def find_all_components(self, target: ISelector, index: int = None) \
            -> Union[IUiComponent, List[IUiComponent]]:
        """
        @func 根据BY指定的条件查找控件, 返回满足条件的所有控件对象列表, 或者列表中第index个控件对象
        @param target: 使用ISelector对象描述的查找条件
        @param index 默认为None, 表示返回所有控件列表，当传入整数时, 返回列表中第index个对象
        @return 返回控件对象IUiComponent或者控件对象列表, 例如[component1, component2], 每个
                如果没有找到满足条件的控件，则返回None
        @example # 查找所有类型为"button"的控件
                 components = driver.find_all_components(BY.type(“button”))
                 # 查找满足条件的第3个控件(index从0开始)
                 component = driver.find_all_components(BY.type(“button”), 2)
                 # 点击控件
                 driver.touch(component)
        """
        driver = self.driver
        if index == 0:
            return self.find_component(target)
        components = driver.findComponents(target)
        if components is None or index is None:
            return components
        if index >= len(components):
            self.driver.log_warning("only %d components found, index out of bound" % len(components))
            return None
        return components[index]

    def find_window(self, filter: WindowFilter) -> UiWindow:
        """
        @func 根据指定条件查找窗口, 返回窗口对象
        @param filter: 使用WindowFilter对象指定查找条件
        @return 如果找到window则返回UiWindow对象, 否则返回None
        @support OHOS
        @example: # 查找标题为日历的窗口
                  window = driver.find_window(WindowFilter().title("日历"))
                  # 查找包名为com.ohos.calender，并且处于活动状态的窗口
                  window = driver.find_window(WindowFilter().bundle_name("com.ohos.calendar").actived(True))
                  # 查找处于活动状态的窗口
                  window = driver.find_window(WindowFilter().actived(True))
                  # 查找聚焦状态的窗口
                  window = driver.find_window(WindowFilter().focused(True))
        """
        driver = self.driver
        return driver.findWindow(filter)

    def get_display_size(self) -> (int, int):
        """
        @func 返回屏幕分辨率
        @return (宽度, 高度)
        @example: # 获取屏幕分辨率
                  width, height = driver.get_display_size()
        """
        return self.driver.getDisplaySize().to_tuple()

    def get_window_size(self) -> (int, int):
        """
        @func 获取当前处于活动状态的窗口大小
        @support OHOS
        @return (宽度, 高度)
        @example: # 获取当前活动状态的窗口大小
                  width, height = driver.get_window_size()
        """
        window = self.find_window(WindowFilter().actived(True))
        if window is None:
            return None
        return window.getBounds().get_size()

    def get_current_window(self) -> UiWindow:
        """
        @func 返回当前处于活动状态的窗口对象
        @support OHOS
        @return 窗口对象
        @example # 获取当前活动的窗口对象
                 window = driver.get_current_window()
                 # 读取窗口所属的应用包名
                 bundle_name = window.getBundleName()
                 # 读取窗口边框
                 bounds = window.getBounds()
        """
        window = self.find_window(WindowFilter().actived(True))
        if window is None:
            window = self.find_window(WindowFilter().focused(True))
        return window

    def get_component_property(self, component: Union[ISelector, IUiComponent], property_name: str) -> Any:
        """
        @func 获取指定控件属性
        @param component: ISelector对象指定的控件或者IUiComponent控件对象
        @param property_name: 属性名称, 目前支持:
                              "id", "text", "key", "type", "enabled", "focused", "clickable", "scrollable"
                              "checked", "checkable"
        @return: 指定控件的指定属性值
        @example: # 获取类型为"checkbox"的控件的checked状态
                  checked = driver.get_component_property(BY.type("checkbox")), "checked")
                  # 获取id为"text_container"的控件的文本属性
                  text = driver.get_component_property(BY.key("text_container"), "text")
        """
        driver = self.driver
        component = _convert_to_uicomponent(driver, component)
        if component is None:
            raise HypiumOperationFailError("Fail to find component")
        supported_properties = {"id": component.getId,
                                "text": component.getText,
                                "key": component.getKey,
                                "type": component.getType,
                                "enabled": component.isEnabled,
                                "focused": component.isFocused,
                                "clickable": component.isClickable,
                                "scrollable": component.isScrollable,
                                "checked": component.isChecked,
                                "checkable": component.isCheckable,
                                "description": component.getDescription,
                                "selected": component.isSelected,
                                "bounds": component.getBounds}
        if property_name not in supported_properties.keys():
            raise HypiumOperationFailError("invalid property: %s, expect: %s" % (property_name,
                                                                                 str(supported_properties.keys())))
        return supported_properties[property_name]()

    def _convert_area_to_rect(self, area: Union[Rect, ISelector, IUiComponent]):
        area_type = type(area)
        if isinstance(area, ISelector) or isinstance(area, IUiComponent):
            component = _convert_to_uicomponent(self.driver, area)
            area = component.getBounds()
        if not isinstance(area, Rect):
            raise HypiumParamError("area", msg=f"type {area_type}, expect type Rect, ISelector, IUiComponent")
        return area

    def capture_screen(self, save_path: str, in_pc: bool = True,
                       area: Union[Rect, ISelector, IUiComponent] = None) -> str:
        """
        @func 通过系统命令获取屏幕截图的图片, 并保存到设备或者PC上指定位置
        @param save_path: 截图保存路径(目录 + 文件名), 注意一jpeg结尾, 当前仅支持jpeg图片
        @param in_pc: 保存路径是否为PC端路径, True表示为PC端路径, False表示设备端路径
        @param area: 指定区域截图, 可以通过控件或者Rect对象指定截图区域
        @return: 截图文件保存的路径
        @example: # 截屏保存到test.jpeg
                  driver.capture_screen("test.jpeg")
                  # 截取id为icon的控件区域的图片, 保存到area.jpeg
                  driver.capture_screen("area.jpeg", area=BY.key("icon"))
                  # 截取屏幕中区域(left, right, top, bottom)的图片, 保存到area2.jpeg
                  driver.capture_screen("area2.jpeg", area=Rect(left, right, top, bottom))
        """
        driver = self.driver
        if not save_path.endswith("jpeg"):
            raise HypiumParamError(msg="Only support jpeg image")
        if not in_pc:
            echo = driver.screenCap(save_path)
            if not self.has_file(save_path):
                raise HypiumOperationFailError(f"Fail to take screenshot: {echo}")
            return save_path
        self.driver.screenshot(save_path)
        if area is not None:
            area = self._convert_area_to_rect(area)
            CVBasic.crop_image(save_path, area)
        return save_path

    def take_screenshot(self, mode: str = "key"):
        """
        @func 模拟用户触发系统截屏的操作, 例如通过按音量下键+电源键
        @param mode: 进行系统截屏的方式，当前支持
                     "key" 例如通过按音量下键+电源键
                     默认通过按音量下键+电源键实现
        @example: # 模拟用户执行截屏操作
                  driver.take_screenshot()
        """
        modes = ["key"]
        if mode not in modes:
            raise HypiumOperationFailError("Unsupported mode: %s, expect: %s" % (mode, str(modes)))
        if mode == "key":
            self.press_key(KeyCode.VOLUME_DOWN, KeyCode.POWER)

    def input_text(self, component: Union[ISelector, IUiComponent, tuple], text: str, mode: InputTextMode = None):
        """
        @func 向指定控件中输入文本内容
        @param component: 需要输入文本的控件，可以使用ISelector对象，
                          或者使用find_component找到的控件对象,
                          以及坐标点(x, y)
        @param text: 需要输入的文本
        @param mode: 输入模式配置, 默认模式如下:
                     1. 默认清空指定的控件中的文本后再执行输入
                     2. 英文字符长度<200时, 逐个输入, 超过200时, 通过剪切板粘贴一次输入
                     3. 中文文本通过剪切板粘贴一次输入
                     通过该参数可以配置
                     1. 追加输入. InputTextMode().addition(True)
                     2. 是否不考虑文本长度直接使用剪切板或者逐个文字输入 InputTextMode().paste(True)
        @example # 在类型为"TextInput"的控件中输入文本"hello world"
                 driver.input_text(BY.type("TextInput"), "hello world")
                 # 在类型为"TextInput"的控件中使用剪切板一次性输入文本"hello world"
                 driver.input_text(BY.type("TextInput"), "hello world", mode=InputTextMode().paste(True))
                 # 在类型为"TextInput"的控件中使用剪切板一次性并追加输入文本"hello world"
                 driver.input_text(BY.type("TextInput"), "hello world", mode=InputTextMode().paste(True).addition(True))
        """
        driver = self.driver
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        if isinstance(component, tuple):
            if len(component) != 2:
                raise ValueError(f"invalid point to click, expect (x, y), not {component}")
            pos = _convert_to_absolute_position(driver, component)
            x, y = pos
            driver.inputText(Point(x, y), text, mode)
        else:
            component = _convert_to_uicomponent(driver, component)
            component.inputText(text, mode)
        if self.driver.device_type == DeviceType.WEARABLE:
            # 等待输入法页面弹出
            time.sleep(0.8)
            # 关闭输入法页面
            self.driver.pressBack()
            # 等待输入法页面关闭
            time.sleep(0.5)

    def clear_text(self, component: [ISelector, IUiComponent]):
        """
        @func 清空指定控件中的文本内容
        @param component: 需要清除文本的控件
        @example: # 清除类型为"InputText"的控件中的内容
                  driver.clear_text(BY.type("InputText"))
        """
        driver = self.driver
        component = _convert_to_uicomponent(driver, component)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        component.clearText()

    def move_cursor(self, direction: str, times: int = 1):
        """
        @func 移动输入框中的光标位置
        @precondition 输入框被选中，其中存在光标
        @param direction: 光标移动的方向, 支持:
                          UiParam.LEFT 向左移动
                          UiParam.RIGHT 向右移动
                          UiParam.UP 向上移动
                          UiParam.DOWN 向下移动
                          UiParam.END 移动到文本尾部
                          UiParam.BEGIN 移动到文本头部
        @param times: 光标移动次数
        """
        key_code_map = {
            UiParam.LEFT: KeyCode.DPAD_LEFT,
            UiParam.RIGHT: KeyCode.DPAD_RIGHT,
            UiParam.UP: KeyCode.DPAD_UP,
            UiParam.DOWN: KeyCode.DPAD_DOWN,
            UiParam.BEGIN: KeyCode.MOVE_HOME,
            UiParam.END: KeyCode.MOVE_END
        }
        for _ in range(times):
            self.press_key(key_code_map[direction])

    def wait_for_idle(self, idle_time: float = DEFAULT_IDLE_TIME, timeout: float = DEFAULT_TIMEOUT):
        """
        @func 等待控件进入空闲状态
        @param idle_time: UI界面处于空闲状态的持续时间，当UI空闲时间>=idle_time时，该函数返回
        @param timeout: 等待超时时间，如果经过timeout秒后UI空闲时间仍然不满足，则返回
        @example: # 等待UI界面进入空闲(稳定)状态
                  driver.wait_for_idle()
                  # 等待UI界面进入空闲(稳定)状态，空闲时间为0.1秒，最长等待时间(超时时间)为10秒
                  driver.wait_for_idle(idle_time=0.1, timeout=10)
        """
        driver = self.driver
        start = time.time()
        idle_time_ms = int(idle_time * 1000)
        timeout_ms = int(timeout * 1000)
        driver.waitForIdle(idle_time_ms, timeout_ms)
        duration = time.time() - start
        duration_ms = int(duration * 1000)
        # wait_for_idle至少等待100毫秒, 避免操作过快, wait_for_idle不生效问题
        if duration_ms < 100:
            time.sleep(0.1)

    def wait_for_component(self, by: ISelector, timeout: float = DEFAULT_TIMEOUT) -> IUiComponent:
        """
        @func 等待目标控件出现，如果超过timeout秒还未出现则抛出异常
        @param by: 等待出现的控件, 通过ISelector类指定
        @param timeout: 等待超时时间, 单位秒
        @example # 等待id为"confirm_button"的控件出现，超时时间为10秒
                 driver.wait_for_component(BY.key("confirm_button"), timeout=10)
                 # 等待id为"confirm_button"的控件出现
                 driver.wait_for_component(BY.key("confirm_button"))
        @return: 控件在超时前出现则返回IUiComponent控件对象，否则返回None
        """
        driver = self.driver
        if timeout <= MAX_TIMEOUT:
            return driver.waitForComponent(by, int(timeout * 1000))
        # 超长的等待拆分成每分钟一次, 避免连接断开
        while timeout > 0:
            component = driver.waitForComponent(by, int(MAX_TIMEOUT * 1000))
            timeout -= MAX_TIMEOUT
            if component is not None:
                return component
            driver.log_info("等待控件中, 剩余等待时间 %ds" % timeout)
        return None

    def wait_for_component_disappear(self, by: ISelector, timeout: float = DEFAULT_TIMEOUT):
        """
        @func 等待控件消失
        @param by: 等待消失的控件, 通过ISelector类指定
        @param timeout: 等待超时时间, 单位秒
        @example # 等待id为"confirm_button"的控件消失，超时时间为10秒
                 driver.wait_for_component_disappear(BY.key("confirm_button"), timeout=10)
        @return None表示控件消失, 否则返回控件对象IUiComponent表示等待超时控件仍未消失
        """
        driver = self.driver
        component = None
        while timeout > 0:
            start = time.time()
            component = driver.waitForComponent(by, 0)
            if component is None:
                return None
            elapse = time.time() - start
            if elapse < 1:
                time.sleep(1 - elapse)
            timeout -= (time.time() - start)
        return component

    def to_abs_pos(self, x: float, y: float) -> (int, int):
        """
        @func 根据屏幕分辨率将相对坐标转换为绝对坐标
        @param x 相对x坐标，范围0~1
        @param y 相对y坐标，范围0~1
        @example # 将相对坐标(0.1, 0.8)转为屏幕上的绝对坐标
                 abs_pos = driver.to_abs_pos(0.1, 0.8)
        @return: 相对坐标对应的绝对坐标
        """
        driver = self.driver
        point = driver.getDisplaySize()
        return int(point.X * x), int(point.Y * y)

    def _two_finger_swipe(self, start1, start2, end1, end2, duration: float = 1, speed=2000):
        duration /= 2
        gesture1 = Gesture().start(start1, 0.001).move_to(end1, duration)
        gesture2 = Gesture().start(start2, 0.001).move_to(end2, duration)
        pointer_matrix = gestures_to_pointer_matrix(self, (gesture1, gesture2))
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                         {"operate_type": "pinch", "start_point_1": (start1[0], start1[1]),
                                          "start_point_2": (start2[0], start2[1]),
                                          "end_point_1": (end1[0], end1[1]), "end_point_2": (end2[0], end2[1])})
        self.driver.injectMultiPointerAction(pointer_matrix, speed)

    def _gen_pinch_in(self, area, scale, direction="diagonal", dead_zone_ratio=0.2, path_vibrate=False):
        if scale < 0 or scale > 1:
            raise HypiumParamError("scale", msg="valid range is [0, 1], get %s" % scale)
        if dead_zone_ratio < 0 or dead_zone_ratio > 0.5:
            raise HypiumParamError("dead_zone_ratio", msg="valid range is [0, 0.5], get %s" % dead_zone_ratio)
        scale = (1 - scale) * 0.5
        if isinstance(area, Rect):
            bounds = area
        else:
            component = _convert_to_uicomponent(self.driver, area)
            bounds = component.getBounds()
        width, height = bounds.get_size()
        if direction == "diagonal":
            start_x1 = bounds.left + int(dead_zone_ratio * width)
            start_y1 = bounds.top + int(dead_zone_ratio * height)
            start_x2 = bounds.right - int(dead_zone_ratio * width)
            start_y2 = bounds.bottom - int(dead_zone_ratio * height)
            end_x1 = start_x1 + int(width * 0.5 * scale)
            end_y1 = start_y1 + int(height * 0.5 * scale)
            end_x2 = start_x2 - int(width * 0.5 * scale)
            end_y2 = start_y2 - int(height * 0.5 * scale)
        elif direction == "horizontal":
            start_x1 = bounds.left + int(dead_zone_ratio * width)
            start_y1 = bounds.top + int(0.5 * height)
            start_x2 = bounds.right - int(dead_zone_ratio * width)
            start_y2 = bounds.bottom - int(0.5 * height)
            end_x1 = start_x1 + int(width * 0.5 * scale)
            end_y1 = start_y1
            end_x2 = start_x2 - int(width * 0.5 * scale)
            end_y2 = start_y2
        else:
            raise HypiumParamError(msg="Invalid direction")

        params = [start_x1, start_y1, start_x2, start_y2, end_x1, end_y1, end_x2, end_y2]
        min_value = min(width, height)
        if scale > 0.1 and dead_zone_ratio > 0.05 and path_vibrate:
            for i in range(len(params)):
                params[i] += random.randint(-int(min_value * 0.05), int(min_value * 0.05))
        return params

    def pinch_in(self, area: Union[ISelector, IUiComponent, Rect], scale: float = 0.4, direction: str = "diagonal",
                 **kwargs):
        """
        @func 在控件上捏合缩小
        @param area: 手势执行的区域
        @param scale: 缩放的比例, [0, 1], 值越小表示缩放操作距离越长, 缩小的越多
        @param fingers: 操作的手指数目, 目前支持双指和三指, 三指时area和scale参数暂时不生效！
        @param direction: 双指缩放时缩放操作方向, 支持
               "diagonal" 对角线滑动
               "horizontal" 水平滑动
        @param kwargs: 其他可选滑动配置参数
               dead_zone_ratio 缩放操作时控件靠近边界不可操作的区域占控件长度/宽度的比例, 默认为0.2, 调节范围为(0, 0.5)
        @example # 在类型为Image的控件上进行双指捏合缩小操作
                 driver.pinch_in(BY.type("Image"))
                 # 在类型为Image的控件上进行双指捏合缩小操作, 设置水平方向捏合
                 driver.pinch_in(BY.type("Image"), direction="horizontal")
        """

        if scale > 1:
            raise HypiumParamError(msg="scale should be in range 0~1")
        if area is None:
            w, h = self.get_display_size()
            area = Rect(right=w, bottom=h)
        params = self._gen_pinch_in(area, scale, direction, **kwargs)
        start_x1, start_y1, start_x2, start_y2, end_x1, end_y1, end_x2, end_y2 = params
        self._two_finger_swipe((start_x1, start_y1), (start_x2, start_y2), (end_x1, end_y1), (end_x2, end_y2))

    def _gen_pinch_out(self, area, scale, direction="diagonal", dead_zone_ratio=0.2, path_vibrate=False):
        if scale < 1 or scale > 2:
            raise HypiumParamError("scale", msg="valid range is [1, 2], get %s" % scale)
        if dead_zone_ratio < 0 or dead_zone_ratio > 0.5:
            raise HypiumParamError("dead_zone_ratio", msg="valid range is [0, 0.5], get %s" % dead_zone_ratio)
        scale = (scale - 1) * 0.5
        if isinstance(area, Rect):
            bounds = area
        else:
            component = _convert_to_uicomponent(self.driver, area)
            bounds = component.getBounds()
        width, height = bounds.get_size()
        if direction == "diagonal":
            start_x1 = bounds.left + int(dead_zone_ratio * width)
            start_y1 = bounds.top + int(dead_zone_ratio * height)
            start_x2 = bounds.right - int(dead_zone_ratio * width)
            start_y2 = bounds.bottom - int(dead_zone_ratio * height)
            end_x1 = start_x1 + int(width * 0.5 * scale)
            end_y1 = start_y1 + int(height * 0.5 * scale)
            end_x2 = start_x2 - int(width * 0.5 * scale)
            end_y2 = start_y2 - int(height * 0.5 * scale)
        elif direction == "horizontal":
            start_x1 = bounds.left + int(dead_zone_ratio * width)
            start_y1 = bounds.top + int(0.5 * height)
            start_x2 = bounds.right - int(dead_zone_ratio * width)
            start_y2 = bounds.bottom - int(0.5 * height)
            end_x1 = start_x1 + int(width * 0.5 * scale)
            end_y1 = start_y1
            end_x2 = start_x2 - int(width * 0.5 * scale)
            end_y2 = start_y2
        else:
            raise HypiumParamError(msg="Invalid direction")
        params = [end_x1, end_y1, end_x2, end_y2, start_x1, start_y1, start_x2, start_y2]
        min_value = min(width, height)
        if scale > 0.1 and dead_zone_ratio > 0.05 and path_vibrate:
            for i in range(len(params)):
                params[i] += random.randint(-int(min_value * 0.05), int(min_value * 0.05))
        return params

    def pinch_out(self, area: Union[ISelector, IUiComponent, Rect], scale: float = 1.6, direction: str = "diagonal",
                  **kwargs):
        """
        @func 在控件上双指放大
        @param area: 手势执行的区域
        @param scale: 缩放的比例, 范围1~2, 值越大表示缩放操作滑动的距离越长, 放大的越多
        @param direction: 双指缩放时缩放操作方向, 支持
               "diagonal" 对角线滑动
               "horizontal" 水平滑动
        @param kwargs: 其他可选滑动配置参数
               dead_zone_ratio 缩放操作时控件靠近边界不可操作的区域占控件长度/宽度的比例, 默认为0.2, 调节范围为(0, 0.5)
        @param fingers: 操作的手指数目, 目前支持双指和三指, 三指时area参数暂时不生效, 可以传入None！
        @example  # 在类型为Image的控件上进行双指放大操作
                  driver.pinch_out(BY.type("Image"))
                  # 在类型为Image的控件上进行双指捏合缩小操作, 设置水平方向捏合
                  driver.pinch_out(BY.type("Image"), direction="horizontal")
        """

        if scale < 1:
            raise HypiumParamError(msg="scale should be in range 1~2")
        if area is None:
            w, h = self.get_display_size()
            area = Rect(right=w, bottom=h)
        params = self._gen_pinch_out(area, scale, direction, **kwargs)
        start_x1, start_y1, start_x2, start_y2, end_x1, end_y1, end_x2, end_y2 = params
        self._two_finger_swipe((start_x1, start_y1), (start_x2, start_y2), (end_x1, end_y1), (end_x2, end_y2))

    def _calculate_fling_time(self, start, end, speed: str):
        end_x, end_y = end
        start_x, start_y = start
        distance = (end_y - start_y) ** 2 + (end_y - start_y) ** 2
        distance = int(math.sqrt(distance))
        speed_map = {
            UiParam.FAST: 0.1,
            UiParam.NORMAL: 0.3,
            UiParam.SLOW: 0.5
        }
        return speed_map[speed]

    def fling(self, direction: str, distance: int = 50, area: Union[ISelector, IUiComponent] = None,
              speed: str = "fast"):
        """
        @func 执行抛滑操作
        @param   direction: 滑动方向，目前支持:
                            "LEFT" 左滑
                            "RIGHT" 右滑
                            "UP" 上滑
                            "DOWN" 下滑
        @param   distance: 相对滑动区域总长度的滑动距离，范围为1-100, 表示滑动长度为滑动区域总长度的1%到100%， 默认为60
        @param   area: 通过控件指定的滑动区域
        @param   speed: 滑动速度, 目前支持三档:
                        UiParam.FAST 快速
                        UiParam.NORMAL 正常速度
                        UiParam.SLOW 慢速
        @example # 向上抛滑
                 driver.fling(UiParam.UP)
                 # 向下慢速抛滑
                 driver.fling(UiParam.DOWN, speed=UiParam.SLOW)
        """
        start, end = self._generate_swipe_position(direction, distance, area=area)
        swipe_time = self._calculate_fling_time(start, end, speed)
        self.slide(start, end, slide_time=swipe_time)

    def inject_gesture(self, gesture: Gesture, speed: int = 2000):
        """
        @func 执行自定义滑动手势操作
        @param gesture: 描述手势操作的Gesture对象
        @param speed: 默认操作速度, 当生成Gesture对象的某个步骤中没有传入操作时间的默认使用该速度进行操作
        @example:   # 创建一个gesture对象
                    gesture = Gesture()
                    # 获取控件计算器的位置
                    pos = driver.find_component(BY.text("计算器")).getBounds().get_center()
                    # 获取屏幕尺寸
                    width, height = driver.get_display_size()
                    # 起始位置, 长按2秒
                    gesture.start(pos, 2)
                    # 移动到屏幕边缘
                    gesture.move_to((width - 20, int(height / 2)))
                    # 停留2秒
                    gesture.pause(2)
                    # 移动到(360, 500)的位置
                    gesture.move_to((360, 500))
                    # 停留2秒结束
                    gesture.pause(2)
                    # 执行gesture对象描述的操作
                    driver.inject_gesture(gesture)
        """
        driver = self.driver
        path = gesture.to_pointer_matrix(self)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        driver.injectMultiPointerAction(path, speed)

    def _convert_to_abs_pos(self, target: Union[tuple, IUiComponent, ISelector, Rect], offset=None):
        """将UI操作对象统一转换为绝对位置坐标"""
        if offset is None:
            offset = (0.5, 0.5)
        driver = self.driver
        if isinstance(target, tuple) or isinstance(target, Point):
            if not _is_scale(target):
                return target
            else:
                x, y = utils.scale_to_position(target, self.get_display_size())
        elif isinstance(target, Rect):
            offset_x, offset_y = offset
            x, y = target.get_pos(offset_x, offset_y)
        else:
            comp = _convert_to_uicomponent(driver, target)
            offset_x, offset_y = offset
            x, y = comp.getBounds().get_pos(offset_x, offset_y)
        return x, y

    def mouse_double_click(self, pos: Union[tuple, IUiComponent, ISelector],
                           button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT):
        """
        @func 鼠标双击
        @param pos: 点击的位置, 例如(100, 200)
        @param button_id: 需要点击的鼠标按键
        @support OHOS
        @example # 使用鼠标左键双击(100, 200)的位置
                 driver.mouse_double_click((100, 200), MouseButton.MOUSE_BUTTON_LEFT)
                 # 使用鼠标右键双击文本为"确认"
                 driver.mouse_double_click(BY.text("确认"), MouseButton.MOUSE_BUTTON_RIGHT)
        """
        pos = self._convert_to_abs_pos(pos)
        cmd = "uinput -M -b %s %s %s 50 100" % (pos[0], pos[1], button_id.value)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.execute_shell_command(cmd)

    def mouse_long_click(self, pos: Union[tuple, IUiComponent, ISelector],
                         button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT, press_time: float = 1.5):
        """
        @func 鼠标长按(rk板测试未生效)
        @param pos: 长按的位置, 例如(100, 200)
        @param button_id: 需要点击的鼠标按键
        @param press_time: 长按的时间
        @support OHOS
        @example # 使用鼠标左键长按(100, 200)的位置
                 driver.mouse_long_click((100, 200), MouseButton.MOUSE_BUTTON_LEFT)
                 # 使用鼠标右键长按文本为"确认"的控件
                 driver.mouse_long_click(BY.text("确认"), MouseButton.MOUSE_BUTTON_RIGHT)
                 # 使用鼠标右键长按相对坐标(0.8, 0.5)的位置
                 driver.mouse_long_click((0.8, 0.5), MouseButton.MOUSE_BUTTON_RIGHT)
        """
        pos = self._convert_to_abs_pos(pos)
        x, y = pos
        cmd = 'uinput -M -m %s %s -d %s -i %s -u %s' \
              % (x, y, button_id.value, int(press_time * 1000), button_id.value)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        result = self.driver.execute_shell_command(cmd)
        self.driver.log_info(result)

    def mouse_click(self, pos: Union[tuple, IUiComponent, ISelector],
                    button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT,
                    key1: Union[KeyCode, int] = None, key2: Union[KeyCode, int] = None):
        """
        @func 鼠标点击, 支持键鼠组合操作
        @param pos: 点击的位置, 支持位置, IUiComponent对象以及ISelector, 例如(100, 200), BY.text("确认")
        @param button_id: 需要点击的鼠标按键
        @param key1:  需要组合按下的第一个键盘按键
        @param key2: 需要组合按下的第二个键盘按键
        @support OHOS
        @example # 使用鼠标左键长按(100, 200)的位置
                 driver.mouse_long_click((100, 200), MouseButton.MOUSE_BUTTON_LEFT)
                 # 使用鼠标右键长按文本为"确认"的控件
                 driver.mouse_long_click(BY.text("确认"), MouseButton.MOUSE_BUTTON_RIGHT)
                 # 使用鼠标右键长按相对坐标(0.8, 0.5)的位置
                 driver.mouse_long_click((0.8, 0.5), MouseButton.MOUSE_BUTTON_RIGHT)
        """
        extra_keys = []
        for item in (key1, key2):
            if item is not None:
                item = self._convert_key_code(item)
                extra_keys.append(item)
        pos = self._convert_to_abs_pos(pos)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return self.driver.mouseClick(Point(*pos), button_id, *extra_keys)

    def mouse_scroll(self, pos: Union[tuple, IUiComponent, ISelector], scroll_direction: str, scroll_steps: int,
                     key1: int = None, key2: int = None, **kwargs):
        """
        @func 鼠标滚动, 支持键鼠组合操作
        @param pos: 滚动的位置, 例如(100, 200)
        @param scroll_direction: 滚动方向
                                 "up" 向上滚动
                                 “down” 向下滚动
        @param scroll_steps: 滚动的鼠标格数
        @param key1:  需要组合按下的第一个键盘按键
        @param key2: 需要组合按下的第二个键盘按键
        @example # 鼠标滚轮在(100, 200)的位置向下滚动10格
                 driver.mouse_scroll((100, 200), UiParam.DOWN, scroll_steps=10)
                 # 鼠标滚轮在类型为Scroll的控件上向上滚动10格
                 driver.mouse_scroll(BY.type("Scroll"), UiParam.UP, scroll_steps=10)
                 # 按住ctrl键, 鼠标滚轮在类型为Scroll的控件上向上滚动10格
                 driver.mouse_scroll(BY.type("Scroll"), UiParam.UP, scroll_steps=10, key1=KeyCode.CTRL_LEFT)
                  # 按住ctrl和shift键, 鼠标滚轮在类型为Scroll的控件上向上滚动10格
                 driver.mouse_scroll(BY.type("Scroll"), UiParam.UP, scroll_steps=10, key1=KeyCode.CTRL_LEFT,
                                key2=KeyCode.SHIFT_LEFT)
        """
        extra_keys = []
        for item in (key1, key2):
            if item is not None:
                item = self._convert_key_code(item)
                extra_keys.append(item)
        if scroll_direction == UiParam.UP:
            down = False
        elif scroll_direction == UiParam.DOWN:
            down = True
        else:
            raise HypiumParamError("scroll_direction",
                                   msg=f"value {scroll_direction}, expect {UiParam.UP, UiParam.DOWN}")
        pos = self._convert_to_abs_pos(pos)
        extra_param = list(kwargs.values())
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return self.driver.mouseScroll(Point(*pos), down, scroll_steps, *extra_keys, *extra_param)

    def mouse_move_to(self, pos: Union[tuple, IUiComponent, ISelector]):
        """
        @func 鼠标指针移动到指定位置
        @param pos: 鼠标指针的位置, 例如(100, 200)
        @example # 鼠标移动到(100, 200)的位置
                 driver.mouse_move_to((100, 200))
                 # 鼠标移动到文本为"查看"的控件
                 driver.mouse_move_to(BY.text("查看"))
                 # 鼠标移动到相对坐标(0.8, 0.5)的位置
                 driver.mouse_long_click((0.8, 0.5))
        """
        pos = self._convert_to_abs_pos(pos)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return self.driver.mouseMoveTo(Point(*pos))

    def mouse_move(self, start: Union[tuple, IUiComponent, ISelector], end: Union[tuple, IUiComponent, ISelector],
                   speed: int = 3000):
        """
        @innerfunc 鼠标指针从之前起始位置移动到结束位置，模拟移动轨迹和速度
        @param start: 起始位置, 支持坐标和控件
        @param end: 结束位置, 支持坐标和控件
        @param speed: 鼠标移动速度，像素/秒
        @example: # 鼠标从控件1移动到控件2
                  driver.mouse_move(BY.text("控件1"), BY.text("控件2"))
        """
        start_pos = self._convert_to_abs_pos(start)
        end_pos = self._convert_to_abs_pos(end)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return self.driver.mouseMoveWithTrack(Point(*start_pos), Point(*end_pos), speed)

    def mouse_drag(self, start: Union[tuple, IUiComponent, ISelector], end: Union[tuple, IUiComponent, ISelector],
                   speed: int = 3000):
        """
        @innerfunc 使用鼠标进行拖拽操作(按住鼠标左键移动鼠标)
        @param start: 起始位置, 支持坐标和控件
        @param end: 结束位置, 支持坐标和控件
        @param speed: 鼠标移动速度，像素/秒
        @example: # 鼠标从控件1拖拽到控件2
                  driver.mouse_drag(BY.text("控件1"), BY.text("控件2"))
        """
        start_pos = self._convert_to_abs_pos(start)
        end_pos = self._convert_to_abs_pos(end)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        return self.driver.mouseDrag(Point(*start_pos), Point(*end_pos), speed)

    def _gen_swipe_to_home(self, end: float = 3):
        driver = self.driver
        point = driver.getDisplaySize()
        width, height = point.X, point.Y
        start_x = int(width / 2)
        end_y = height - int(height / end)
        return (start_x, height - 10), (int(start_x * 1.2), end_y)

    def swipe_to_home(self, times: int = 1):
        """
        @func 屏幕低端上滑回到桌面
        @precondition 设备开启触摸屏手势导航
        @param times: 上滑次数, 默认1次, 某些场景可能需要两次上滑才能返回桌面
        @example # 上滑返回桌面
                 driver.swipe_to_home(driver)
                 # 连续上滑2次返回桌面
                 driver.swipe_to_home(driver, times=2)
        """
        driver = self.driver
        start, end = self._gen_swipe_to_home(end=6)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                         {"operate_type": "swipe", "start_point": (start[0], start[1]),
                                          "end_point": (end[0], end[1])})
        driver.swipe(*start, *end, NAV_GESTURE_SPEED)
        for i in range(times - 1):
            time.sleep(SWIPE_INTERVAL)
            driver.swipe(*start, *end, NAV_GESTURE_SPEED)
        time.sleep(1)

    def _gen_swipe_to_back(self, side, height):
        if side == UiParam.RIGHT:
            start = self.to_abs_pos(0.99, height)
            end = self.to_abs_pos(0.6, height * 1.2)
        elif side == UiParam.LEFT:
            start = self.to_abs_pos(0.01, height)
            end = self.to_abs_pos(0.4, height * 1.2)
        else:
            raise HypiumOperationFailError("invalid side %s, expect[%s, %s]" %
                                           (side, UiParam.LEFT, UiParam.RIGHT))
        return start, end

    def swipe_to_back(self, side=UiParam.LEFT, times: int = 1, height: float = 0.5):
        """
        @func 滑动屏幕右侧返回
        @precondition 设备开启触摸屏手势导航
        @param side: 滑动的位置, "RIGHT"表示在右边滑动返回，"LEFT"表示在左边滑动返回
        @param times: 上滑次数, 默认1次, 某些场景可能需要两次上滑才能返回桌面
        @param height: 滑动位置在屏幕中Y轴的比例高度(从屏幕顶部开始计算)
        @example:# 侧滑返回
                 driver.swipe_to_back()
                 # 侧滑2次返回
                 driver.swipe_to_back(times=2)
                 # 设置侧滑位置的高度比例为屏幕高度的80%，即在屏幕靠下的位置侧滑返回
                 driver.swipe_to_back(driver, height=0.8)
        """
        start, end = self._gen_swipe_to_back(side, height)
        cmd = "uinput -T -m %s %s %s %s %s" % (start[0], start[1], end[0], end[1], 200)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START,
                                         {"operate_type": "swipe", "start_point": (start[0], start[1]),
                                          "end_point": (end[0], end[1])})
        self.driver.execute_shell_command(cmd)
        for _ in range(times - 1):
            time.sleep(SWIPE_INTERVAL / 2)
            self.driver.execute_shell_command(cmd)

    def swipe_to_recent_task(self):
        """
        @func 屏幕底端上滑停顿, 打开多任务界面
        @precondition 设备开启触摸屏手势导航
        @example: # 上滑停顿进度多任务界面
                  driver.swipe_to_recent_task()
        """
        gesture = Gesture()
        start, end = self._gen_swipe_to_home(end=4)
        gesture.start(start).move_to(end).pause(1)
        self.inject_gesture(gesture)

    def check_current_window(self, title: str = None, bundle_name: str = None):
        """
        @func:     检查当前活动的窗口的属性是否符合预期
        @param:    title: 预期的窗口标题, None表示不检查
        @param:    bundle_name: 预期窗口所属的app包名, None表示不检查
        @support:  OHOS
        @example   # 检查当前活动窗口的标题为"畅连"
                   driver.check_current_window(title="畅连")
                   # 检查当前活动窗口对应的应用包名为"com.ohos.settings"
                   driver.check_current_window(bundle_name="com.ohos.settings")
        """
        current_window = self.driver.findWindow(WindowFilter().actived(True))
        if not current_window:
            current_window = self.driver.findWindow(WindowFilter().focused(True))
        if current_window is None:
            self.driver.log_info("No actived or focused window!")
            return False
        return self.check_window(current_window, title, bundle_name)

    def check_window(self, window: WindowFilter, title: str = None, bundle_name: str = None):
        """
        @func:     检查指定的window的属性是否符合预期
        @param:    title: 预期的窗口标题, None表示不检查
        @param:    bundle_name: 预期窗口所属的app包名, None表示不检查
        @support:  OHOS
        @example   # 检查当前焦点窗口的包名为com.ohos.setting
                   driver.check_window(WindowFilter().focused(True), bundle_name="com.ohos.settings")
        """
        driver = self.driver

        if isinstance(window, WindowFilter):
            condition = window
            window = driver.findWindow(window)
            if window is None:
                MESSAGE("指定窗口不存在 %s" % str(condition.to_dict(9)))
                return False
        if not isinstance(window, UiWindow):
            raise HypiumParamError("invalid param type window, can only be WindowFilter or UiWindow")
        if title is not None:
            actual_title = window.getTitle()
            ACTUAL(f"期望 title = {title}, 实际 title = {actual_title}")
            if actual_title != title:
                return False
        if bundle_name is not None:
            actual_bundle_name = window.getBundleName()
            ACTUAL(f"期望 bundle_name = {bundle_name}, 实际 bundle_name = {actual_bundle_name}")
            if actual_bundle_name != bundle_name:
                return False
        return True

    def check_exist(self, component: ISelector, expect_exist: bool = True):
        """和check_component_exist相同"""
        return self.check_component_exist(component, expect_exist)

    def check_component_exist(self, component: ISelector, expect_exist: bool = True, wait_time: int = 0,
                              scroll_target: Union[ISelector, IUiComponent] = None, ):
        """
        @func:     检查指定UI控件是否存在
        @param:    component: 待检查的UI控件, 使用ISelector对象指定
        @param:    expect_exist: 是否期望控件存在, True表示期望控件存在，False表示期望控件不存在
        @param:    wait_time: 检查过程中等待控件出现的时间
        @param:    scroll_target: 上下滑动检查目标控件时滑动的控件, 默认为None表示不进行滑动查找
        @example   # 检查类型为Button的控件存在
                   driver.check_component_exist(BY.type("Button"))
                   # 检查类型为Button的控件存在，如果不存在等待最多5秒
                   driver.check_component_exist(BY.type("Button"), wait_time=5)
                   # 在类型为Scroll的控件上滚动检查文本为"hello"的控件存在
                   driver.check_component_exist(BY.text("hello"), scroll_target=BY.type("Scroll"))
                   # 检查文本为确认的控件不存在
                   driver.check_component_exist(BY.text("确认"), expect_exist=False)
        """
        driver = self.driver
        if isinstance(scroll_target, IUiComponent):
            target = scroll_target.scrollSearch(component)
        elif isinstance(scroll_target, ISelector):
            scroll_target_by = scroll_target
            scroll_target = driver.waitForComponent(scroll_target_by, int(wait_time * 1000))
            if scroll_target is None:
                target = driver.waitForComponent(component, int(wait_time * 1000))
                if target is None:
                    return expect_exist is False
            else:
                target = scroll_target.scrollSearch(component)
        elif scroll_target is None:
            target = driver.waitForComponent(component, int(wait_time * 1000))
        else:
            raise HypiumParamError(msg="Invalid scroll target: [%s], expect [ISelector, IUiComponent] " % scroll_target)
        if target is None:
            return expect_exist is False
        else:
            return expect_exist is True

    def check_component(self, component: Union[ISelector, IUiComponent], expect_equal: bool = True,
                        wait_time: float = 0,
                        **kwargs):
        """
        @func 检查控件属性是否符合预期
        @param component: 需要检查的控件, 支持ISelector或者IUiComponent对象
        @param expect_equal: 预期值和实际值是否相等，True表示预期相等，False表示预期不相等
        @param wait_time: 等待控件出现的时间, 默认为0
        @param kwargs: 指定预期的控件属性值, 目前支持:
                      "id", "text", "key", "type", "enabled", "focused", "clickable", "scrollable"
                      "checked", "checkable"
        @example # 检查id为xxx的控件的checked属性为True
                 driver.check_component(BY.key("xxx"), checked=True)
                 # 检查id为check_button的按钮enabled属性为True
                 driver.check_component(BY.key("checked_button"), enabled=True)
                 # 检查id为container的控件文本内容为正在检查
                 driver.check_component(BY.key("container"), text="正在检查")
                 # 检查id为container的控件文本内容不为空
                 driver.check_component(BY.key("container"), text="", expect_equal=False)
        """
        if isinstance(component, ISelector):
            by = component
            component = self.driver.waitForComponent(by, int(wait_time * 1000))
            if component is None:
                MESSAGE("控件[%s]不存在" % str(by))
                return False
        equal_desc = "=" if expect_equal else '!='
        for key, value in kwargs.items():
            actual_value = self.get_component_property(component, key)
            result = (actual_value == value)
            if result is not expect_equal:
                MESSAGE(f"控件属性检查失败, 预期{key} {equal_desc} {value}, 实际{key}={actual_value}")
                return False
        return True

    def check_window_exist(self, window: WindowFilter, expect_exist: bool = True):
        """
        @func:     检查指定的window是否存在
        @param:    window: 待检查的UI控件，使用ISelector对象指定
        @param:    expect_exist: 是否期望窗口存在, True表示期望窗口存在，False表示期望窗口不存在
        @support:  OHOS
        @example:  # 检查包名为com.ohos.settings的窗口存在
                   driver.check_window_exist(WindowFilter().bundle_name("com.ohos.settings"))
                   # 检查标题为畅连的窗口不存在
                   driver.check_window_exist(WindowFilter().title("畅联"), expect_exist=False)
                   # 检查包名为com.ohos.settings, 标题为设置的窗口存在
                   driver.check_window_exist(WindowFilter().title("设置").bundle_name("com.ohos.settings"))
        """
        driver = self.driver
        if driver.findWindow(window) is None:
            return expect_exist is False
        else:
            return expect_exist is True

    def _check_image_exist(self, src_path, similar=0.95,
                           timeout=3, mode: str = "template", **kwargs):
        """
        @summary: 点击图片
        @param  src_path: 原图片路径
                similar: 相似度
        @return: 布尔类型,比对结果
        """
        count = 0
        device = self.driver._device
        while count < timeout:
            std_path = os.path.abspath(src_path)
            path = self.capture_screen(os.path.join(utils.get_tmp_dir(), "devicetest.jpeg"))
            count += 1
            if mode == "template":
                img_src = CVBasic.imread(path)
                img_tmp = CVBasic.imread(std_path)
                gray_img1 = cv2.cvtColor(img_src, cv2.COLOR_BGR2GRAY)
                gray_img2 = cv2.cvtColor(img_tmp, cv2.COLOR_BGR2GRAY)
                result = cv2.matchTemplate(gray_img1, gray_img2, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                device.log.debug("max_loc: {}, max_value: {}".format(max_loc, max_val))
                if max_val >= similar:
                    return True
            else:
                result = CVBasic.find_image(std_path, path, **kwargs)
                if result is not None:
                    return True
            time.sleep(1)
        return False

    def check_image_exist(self, image_path_pc: str, expect_exist: bool = True,
                          similarity: float = 0.95, timeout: int = 3, mode="template", **kwargs):
        """
        @func:    使用图片模板匹配算法检测当前屏幕截图中是否有指定图片，需要保证模板图片的分辨率和屏幕截图中目标图像的
                  分辨率一致，否则会无法成功检测到目标图片
        @param:   image_path_pc: 待检查的图片路径（图片保存在PC端）
        @param:   expect_exist: 是否期望图片在设备屏幕上存在, True表示期望控件存在，False表示期望控件不存在
        @param:   similarity: 图像匹配算法比较图片时使用的相似度, 范围0~1,
        @param:   timeout: 检查的总时间，每秒会进行获取一次屏幕截图检查指定图片是否存在，通过timeout可指定检查的次数
        @param:   mode: 图片匹配模式, 支持template和sift, 图片分辨率/旋转变化对sift模式影响相对较小，但sift模式难以处理缺少较复杂图案
                        的纯色，无线条图片
        @param:   kwargs: 其他配置参数
                  min_match_point: 最少匹配特征点数, 值越大匹配越严格, 默认为16, 仅sift模式有效

        @example: # 检查图片存在
                  driver.check_image_exist("test.jpeg")
                  # 检查图片不存在
                  driver.check_image_exist("test.jpeg", expect_exist=False)
                  # 检查图片存在, 图片相似度要求95%, 重复检查时间5秒
                  driver.check_image_exist("test.jpeg", timeout=5, similarity=0.95)
                  # 检查图片不存在, 重复检查时间5秒
                  driver.check_image_exist("test.jpeg", timeout=5, expect_exist=False)
                  # 使用sift算法检查图片存在, 设置最少匹配特征点数量为16
                  driver.check_image_exist("test.jpeg", mode="sift", min_match_point=16)
        """
        driver = self.driver
        MESSAGE("检测图片是否存在于当前页面中")
        EXPECT("图片存在于当前页面中") if expect_exist else EXPECT("图片不存在于当前页面中")
        if self._check_image_exist(image_path_pc, similarity, timeout, mode, **kwargs):
            ACTUAL("图片存在于当前页面中")
            return expect_exist is True
        else:
            ACTUAL("图片不存在于当前页面中")
            return expect_exist is False

    def start_listen_toast(self):
        """
        @func 开启新的toast监听, 需要配合get_latest_toast使用
              (该操作会清理上次记录的toast消息, 保证get_latest_toast获取本次listen_toast之后产生的toast消息)
        @example  # 开启Toast监听
                  driver.start_listen_toast()
                  # 执行操作
                  driver.touch(BY.text("发送"))
                  # 返回上次开启监听后最新的一条toast消息，如果没有消息则等待最多5秒直到新toast出现, 返回该toast的文本
                  text_in_toast = driver.get_latest_toast(time_out=5)
                  # 断言text_in_toast等于"发送成功"
                  host.check_equal(text_in_toast, "发送成功")
        """
        driver = self.driver
        device = driver._device
        if not hasattr(self, "_ui_event_listening") or not self._ui_event_listening:
            self._ui_event_listening = True
        else:
            driver.log_error("last listening result has not been read, use [get_latest_toast] to read it")
        if device_helper.get_device_agent_mode(device) == "abc":
            return device.abc_proxy.UiTestDeamon.uiEventObserverOnce(showType="toastShow")
        elif device_helper.get_device_agent_mode(device) == "bin":
            # 读取_agent_mode, 默认为hap
            return self.driver.uiEventObserverOnce("toastShow")
        else:
            return device.proxy.UiTestDeamon.uiEventObserverOnce(showType="toastShow")

    def get_latest_toast(self, timeout: float = 3) -> str:
        """
        @func 读取最近一段时间内最新的一条toast消息内容
        @param timeout: 没有满足的toast出现时，等待toast出现的最长时间，单位为秒
        @return toast消息的文本内容, 如果没有满足的toast消息则返回空字符串""
        @example:
                  # 开启Toast监听
                  driver.start_listen_toast()
                  # 执行操作
                  driver.touch(BY.text("发送"))
                  # 返回上次开启监听后最新的一条toast消息，如果没有消息则等待最多5秒直到新toast出现, 返回该toast的文本
                  text_in_toast = driver.get_latest_toast(time_out=5)
                  # 检查text_in_toast等于发送成功
                  host.check_equal(text_in_toast, "发送成功")
        """
        driver = self.driver
        device = driver._device
        if not hasattr(self, "_ui_event_listening") or not self._ui_event_listening:
            driver.log_error("toast listening has not started, use [start_listen_toast] to start")
        if device_helper.get_device_agent_mode(device) == "abc":
            result = device.abc_proxy.UiTestDeamon.getRecentUiEvent(timeout=timeout)
        elif device_helper.get_device_agent_mode(device) == "bin":
            # 读取agent_mode, 默认为hap
            result = self.driver.getRecentUiEvent(int(timeout))
        else:
            result = device.proxy.UiTestDeamon.getRecentUiEvent(timeout=timeout)
        self._ui_event_listening = False
        if isinstance(result, JsonBase):
            if hasattr(result, "text"):
                return result.text
            else:
                return ""
        if result is False or result is None or result == "":
            return ""
        try:
            result = json.loads(result)
            return result["text"]
        except Exception as e:
            driver.log_error("invalid reply: " + result)
            return ""

    def check_toast(self, expect_text: str, fuzzy: str = 'equal', timeout: int = 3):
        """
        @func 检查最新的一条toast消息内容
        @param expect_text: 期望的toas文本内容
        @param fuzzy: 模糊匹配方式
                       "equal: 全等匹配
                       "starts_with" 匹配开头
                       "ends_with" 匹配结尾
                       "contains" 匹配包含(实际toast消息包含期望文本)
        @param timeout: 没有满足的toast出现时，等待toast出现的最长时间，单位为秒
        @example:
                  # 开启Toast监听
                  driver.start_listen_toast()
                  # 执行操作
                  driver.touch(BY.text("发送"))
                  # 检查toast
                  driver.check_toast("发送成功", )
        """
        text = self.get_latest_toast(timeout=timeout)
        if fuzzy is None or fuzzy == "equal":
            result = (expect_text == text)
        elif fuzzy == "starts_with":
            result = text.startswith(expect_text)
        elif fuzzy == "ends_with":
            result = text.endswith(expect_text)
        elif fuzzy == "contains":
            result = expect_text in text
        else:
            raise HypiumParamError("fuzzy", msg="expected [equal, starts_with, ends_with, contains], get [%s]" % fuzzy)
        if not result:
            MESSAGE("检查失败: 期望值 %s, 实际值 %s, 匹配模式 %s" % (expect_text, text, fuzzy))
        return result

    def start_listen_ui_event(self, event_type: str):
        """
        @func 开始ui事件监听
              (该操作会清理上次记录的toast消息, 保证get_latest_ui_event获取开始监听后产生的最新ui事件)
        @param event_type: ui事件类型, 目前支持
                           toastShow toast消息出现
                           dialogShow 对话框出现
        @example  # 开启toast消息事件监听
                  driver.start_listen_ui_event("toastShow")
                  # 开启对话框出现事件监听
                  driver.start_listen_ui_event("dialogShow")
        """
        driver = self.driver
        device = driver._device
        if not hasattr(self, "_ui_event_listening") or not self._ui_event_listening:
            self._ui_event_listening = True
        else:
            driver.log_error("last listening result has not been read, use [get_latest_ui_event] to read it")
        if device_helper.get_device_agent_mode(device) == "abc":
            return device.abc_proxy.UiTestDeamon.uiEventObserverOnce(showType=event_type)
        elif device_helper.get_device_agent_mode(device) == "bin":
            # 读取agent_mode, 默认为hap
            return self.driver.uiEventObserverOnce(event_type)
        else:
            return device.proxy.UiTestDeamon.uiEventObserverOnce(showType=event_type)

    def get_latest_ui_event(self, timeout: float = 3) -> dict:
        """
        @func 读取开始监听ui事件后最新出现的UI事件
        @return ui事件信息, 例如:
                dialogShow 事件 {"bundleName":"com.uitestScene.acts","text":"dialogShow","type":"AlertDialog"}
                toastShow 事件 {"bundleName":"com.uitestScene.acts","text":"toastShow","type":"Toast"}
                没有事件返回None
        @example  # 开启对话框出现(dialogShow)事件监听
                  driver.start_listen_ui_event("dialogShow")
                  # 点击发送
                  driver.touch(BY.text("发送"))
                  # 读取ui事件，如果没有ui事件则等待最多5秒直到有ui事件出现, 返回ui事件信息
                  ui_event = driver.get_latest_ui_event(timeout=5)
        """
        driver = self.driver
        device = driver._device
        if not hasattr(self, "_ui_event_listening") or not self._ui_event_listening:
            driver.log_error("ui event listening has not started, use [start_listen_ui_event] to start")
        if device_helper.get_device_agent_mode(device) == "abc":
            result = device.abc_proxy.UiTestDeamon.getRecentUiEvent(timeout=timeout)
        elif device_helper.get_device_agent_mode(device) == "bin":
            # 读取agent_mode, 默认为hap
            result = self.driver.getRecentUiEvent(int(timeout))
        else:
            result = device.proxy.UiTestDeamon.getRecentUiEvent(timeout=timeout)
        self._ui_event_listening = False
        if isinstance(result, JsonBase):
            return result.to_dict()
        if result is False or len(result) == 0:
            return None
        else:
            return utils.parse_json(result)

    def inject_multi_finger_gesture(self, gestures: List[Gesture], speed: int = 6000):
        """
        @func 注入多指手势操作
        @param gestures: 表示单指手势操作的Gesture对象列表，每个Gesture对象描述一个手指的操作轨迹
                         注意如果各个手势持续时间不同，时间短的手势操作会保持在结束位置，等待所有手势完成后才会抬起对应手指。
        @param speed: gesture的步骤没设置时间时, 使用该速度计算时间, 单独 像素/秒
        @example: # 创建手指1的手势, 从(0.4, 0.4)的位置移动到(0.2, 0.2)的位置
                  gesture1 = Gesture().start((0.4, 0.4)).move_to((0.2, 0.2), interval=1)
                  # 创建手指2的手势, 从(0.6, 0.6)的位置移动到(0.8, 0.8)的位置
                  gesture2 = Gesture().start((0.6, 0.6)).move_to((0.8, 0.8), interval=1)
                  # 注入多指操作
                  driver.inject_multi_finger_gesture((gesture1, gesture2))
        """
        pointer_matrix = gestures_to_pointer_matrix(self, gestures, speed)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.injectMultiPointerAction(pointer_matrix, speed)

    def two_finger_swipe(self, start1: tuple, end1: tuple,
                         start2: tuple, end2: tuple, duration: float = 0.5, area: Rect = None):
        """
        @func 执行双指滑动操作
        @param start1: 手指1起始坐标
        @param end1: 手指1起始坐标
        @param start2: 手指2起始坐标
        @param end2: 手指2结束坐标
        @param duration: 滑动操作持续时间
        @param area: 滑动的区域, 当起始结束坐标为(0.1, 0.2)等相对比例坐标时生效
        @example: # 执行双指滑动操作, 手指1从(0.4, 0.4)滑动到(0.2, 0.2), 手指2从(0.6, 0.6)滑动到(0.8, 0.8)
                  driver.two_finger_swipe((0.4, 0.4), (0.2, 0.2), (0.6, 0.6), (0.8, 0.8))
                  # 执行双指滑动操作, 手指1从(0.4, 0.4)滑动到(0.2, 0.2), 手指2从(0.6, 0.6)滑动到(0.8, 0.8), 持续时间3秒
                  driver.two_finger_swipe((0.4, 0.4), (0.2, 0.2), (0.6, 0.6), (0.8, 0.8), duration=3)
                  # 查找Image类型控件
                  comp = driver.find_component(BY.type("Image"))
                  # 在指定的控件区域内执行双指滑动(滑动起始/停止坐标为控件区域内的相对坐标)
                  driver.two_finger_swipe((0.4, 0.4), (0.1, 0.1), (0.6, 0.6), (0.9, 0.9), area=comp.getBounds())
        """
        duration /= 2
        gesture1 = Gesture(area).start(start1, 0.001).move_to(end1, duration)
        gesture2 = Gesture(area).start(start2, 0.001).move_to(end2, duration)
        pointer_matrix = gestures_to_pointer_matrix(self, (gesture1, gesture2))
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.injectMultiPointerAction(pointer_matrix, 2000)

    def multi_finger_touch(self, points: List[tuple], duration: float = 0.1, area: Rect = None):
        """
        @func 执行多指点击操作
        @param points: 需要点击的坐标位置列表，每个坐标对应一个手指, 例如[(0.1, 0.2), (0.3, 0.4)], 最多支持4指点击
        @param duration: 按下/抬起的时间，可实现多指长按操作, 单位秒
        @param area: 点击的区域, 当坐标为(0.1, 0.2)等相对比例坐标时生效, 默认为区域为全屏
        @example: # 执行多指点击操作, 同时点击屏幕(0.1， 0.2), (0.3, 0.4)的位置
                  driver.multi_finger_touch([(0.1， 0.2), (0.3, 0.4)])
                  # 执行多指点击操作, 设置点击按下时间为1秒
                  driver.multi_finger_touch([(0.1， 0.2), (0.3, 0.4)], duration=2)
                  # 查找Image类型控件
                  comp = driver.find_component(BY.type("Image"))
                  # 在指定的控件区域内执行多指点击(点击坐标为控件区域内的相对坐标)
                  driver.multi_finger_touch([(0.5, 0.5), (0.6, 0.6)], area=comp.getBounds())
        """
        gestures = []
        if len(points) > 4 or len(points) < 1:
            raise ValueError(f"Only support 1 ~ 4 finger, get {len(points)} fingers")
        for item in points[:-1]:
            # set duration to 1 ms, to avoid different finger NOT touching down at same time
            gestures.append(Gesture(area).start(item, 0.001))
        gestures.append(Gesture(area).start(points[-1], duration))
        pointer_matrix = gestures_to_pointer_matrix(self, gestures)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.injectMultiPointerAction(pointer_matrix, 2000)

    def pen_click(self, target: Union[ISelector, IUiComponent, tuple], offset: tuple = None):
        """
        @func 模拟触控笔点击
        @param target: 点击操作目标
        @param offset: 点击坐标在操作目标中的偏移坐标
        """
        x, y = self._convert_to_abs_pos(target, offset)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.penClick(Point(x, y))

    def pen_double_click(self, target: Union[ISelector, IUiComponent, tuple], offset: tuple = None):
        """
        @func 模拟触控笔双击
        @param target: 点击操作目标
        @param offset: 点击坐标在操作目标中的偏移坐标
        """
        x, y = self._convert_to_abs_pos(target, offset)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.penDoubleClick(Point(x, y))

    def pen_long_click(self, target: Union[ISelector, IUiComponent, tuple], offset: tuple = None,
                       pressure: float = None):
        """
        @func 模拟触控笔长按
        @param target: 点击操作目标
        @param offset: 点击坐标在操作目标中的偏移坐标
        """
        x, y = self._convert_to_abs_pos(target, offset)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.penLongClick(Point(x, y), pressure)

    def _convert_to_speed(self, start, end, duration, speed):
        if duration is None:
            duration = DEFAULT_SLIDE_TIME

        if isinstance(speed, int) or isinstance(speed, float):
            speed = int(speed)
            if speed < 200 or speed > 40000:
                raise ValueError("speed must in the range [200,40000], get %s" % speed)
        else:
            speed = utils.convert_to_speed(duration, start, end)
        return speed

    def _convert_to_duration(self, start, end, duration, speed):
        if duration is None:
            duration = DEFAULT_SLIDE_TIME

        if isinstance(speed, int) or isinstance(speed, float):
            speed = int(speed)
            if speed < 200 or speed > 40000:
                raise ValueError("speed must in the range [200,40000], get %s" % speed)
            duration = utils.convert_to_duration(speed, start, end)
        return duration

    def pen_swipe(self, direction: str, distance: int = 60, start_point: tuple = None,
                  area: Union[ISelector, IUiComponent, Rect] = None, pressure: float = None,
                  duration: float = DEFAULT_SLIDE_TIME, speed: int = None):
        """
        @func 模拟触控笔滑动
        """
        driver = self.driver
        start, end = self._generate_swipe_position(direction, distance, None, start_point, area)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        speed = self._convert_to_speed(start, end, duration, speed)
        driver.penSwipe(Point(*start), Point(*end), speed, pressure)

    def pen_slide(self, start: Union[ISelector, IUiComponent, tuple],
                  end: Union[ISelector, IUiComponent, tuple],
                  area: Union[ISelector, IUiComponent, Rect] = None,
                  pressure: float = None,
                  duration: float = DEFAULT_SLIDE_TIME,
                  speed: int = None):
        """
        @func 模拟触控笔滑动
        """
        start_x, start_y, end_x, end_y = _generate_drag_position(self.driver, start, end, area)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        speed = self._convert_to_speed((start_x, start_y), (end_x, end_y), duration, speed)
        self.driver.penSwipe(Point(start_x, start_y), Point(end_x, end_y), speed, pressure)

    def pen_drag(self, start: Union[ISelector, IUiComponent, tuple], end: Union[ISelector, IUiComponent, tuple],
                 area: Union[ISelector, IUiComponent, Rect] = None,
                 pressure: float = None, press_time: float = 1.5, duration: float = None, speed: int = None):
        """
        @func 模拟触控笔点击
        """
        start_x, start_y, end_x, end_y = _generate_drag_position(self.driver, start, end, area)
        duration = self._convert_to_duration((start_x, start_y), (end_x, end_y), duration, speed)
        gesture = Gesture()
        gesture.start((start_x, start_y), press_time)
        gesture.move_to((end_x, end_y), duration)
        self.pen_inject_gesture(gesture, pressure)

    def pen_inject_gesture(self, gesture: Gesture, pressure: float = None, speed: int = None):
        """
        @func 模拟触控笔自定义手势
        @param gesture: 触控笔自定义手势
        @param pressure: 触控笔压力值, 范围0~1
        @param speed: 移动速度, 默认600px/s
        @example: # 模拟注入触控笔滑动操作
                  gesture = Gesture()
                  # 在(0.5, 0.5)位置按下
                  gesture.start((0.5, 0.5))
                  # 移动到(0.8, 0.8)的位置
                  gesture.move_to((0.8, 0.8))
                  # 停顿1秒
                  gesture.pause()
                  # 注入操作
                  driver.pen_inject_gesture(gesture)
        """
        driver = self.driver
        path = gesture.to_pointer_matrix(self)
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        driver.injectPenPointerAction(path, speed, pressure)

    def _convert_direction(self, direction):
        """
        LEFT	0	向左。
        RIGHT	1	向右。
        UP	2	向上。
        DOWN	3	向下。
        """
        direction_map = {
            UiParam.LEFT: 0,
            UiParam.RIGHT: 1,
            UiParam.UP: 2,
            UiParam.DOWN: 3
        }
        return direction_map.get(direction, 2)

    def touchpad_swipe(self, direction: str, fingers=3, speed=None):
        """
        @func 模拟PC触控板滑动后手势
        @param direction: 滑动方向, 支持
                            UiParam.LEFT
                            UiParam.RIGHT
                            UiParam.UP
                            UiParam.DOWN
        @param fingers: 滑动手指数量
        @param speed: 滑动速度
        @device_type: 2in1
        @example: # 触控板三指上滑
                  driver.touchpad_swipe_and_hold(UiParam.UP, fingers=3)
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.touchPadMultiFingerSwipe(fingers, self._convert_direction(direction),
                                             TouchPadSwipeOptions().stay(False).speed(speed))

    def touchpad_swipe_and_hold(self, direction: str, fingers=3, speed=None):
        """
        @func 模拟PC触控板滑动后停顿手势
        @param direction: 滑动方向, 支持
                            UiParam.LEFT
                            UiParam.RIGHT
                            UiParam.UP
                            UiParam.DOWN
        @param fingers: 滑动手指数量
        @param speed: 滑动速度
        @device_type: 2in1
        @example: # 触控板三指上滑后停顿
                  driver.touchpad_swipe_and_hold(UiParam.UP, fingers=3)
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.touchPadMultiFingerSwipe(fingers, self._convert_direction(direction),
                                             TouchPadSwipeOptions().stay(True).speed(speed))

    def rotate_crown(self, steps: int, speed: int = None):
        """
        @param steps: The number of cells that watch rotates.Positive value indicate clockwise rotation,negative
                      value indicate counterclockwise rotation.
        @param speed: The speed of watch crown rotates(cells per second),ranges from 1 to 500.
                      Set it default 20 if out of range or undefined or null.
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        self.driver.crownRotate(steps, speed)

    def input_text_on_current_cursor(self, text: str):
        """
        @func 在光标处输入文本
        """
        self._event_manager.notify_event(EventManager.EVENT_UI_ACTION_START)
        device_api_level = self.driver.get_api_level()
        if device_api_level < 20:
            raise HypiumOperationFailError(
                "Not support this method [input_text_on_current_cursor], device api level %s < required api level %s" % (
                    device_api_level, 20))
        self.driver.execute_shell_command("uitest uiInput text \"%s\"" % text)
