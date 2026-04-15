import warnings
import weakref
from typing import Union, List
from devicetest.core.test_case import keyword, checkepr
from abc import ABC, abstractmethod
from hypium.uidriver.interface import IUiDriver, ILog
from hypium.uidriver.uicomponent import IUiComponent
from hypium.uidriver.uiwindow import UiWindow
from hypium.uidriver import device_connector
from hypium.model import Rect, MouseButton, KeyCode, DisplayRotation, WindowFilter, DeviceType, constant, InputTextMode
from hypium.exception import *
from hypium.uidriver.gesture import Gesture
from .plugin_mix_in import PluginMixIn
from hypium.model.driver_config import DriverConfig
from hypium.uidriver.interface.uitree import ISelector
from hypium.version import __version__
from hypium.dfx.tracker import Tracker

try:
    from devicetest.record_actions.record_action import record_action
except Exception:
    def record_action(func):
        return func

try:
    from devicetest.record_actions.record_action import ai_adaptive
except Exception:
    def ai_adaptive(func):
        return func

DEFAULT_IDLE_TIME = 0.7
DEFAULT_SLIDE_TIME = 0.3
DEFAULT_TIMEOUT = 10


class UiDriver(IUiDriver,
               PluginMixIn):
    """
    设备Ui测试核心功能类, 提供控件查找/设备点击/滑动操作, app启动停止等常用功能
    """

    def close_display(self):
        """
        @func 关闭屏幕, 如果屏幕已经关闭则无动作
        @example # 关闭屏幕
                 driver.close_display()
        """
        return self._driver_impl.close_display()

    def unlock(self):
        """
        @func 唤醒并解锁屏幕
        @example # 唤醒并解锁屏幕
                 driver.unlock()
        """
        return self._driver_impl.unlock()

    def set_sleep_time(self, sleep_time: float):
        """
        @func: 设置熄屏时间, 注意该接口设置的熄屏时间仅临时生效, 不会修改系统设置中设置的熄屏时间,
               在屏幕熄屏一次后将恢复设置应用中的熄屏时间
        @param sleep_time 熄屏时间, 单位秒
        @example: # 设置熄屏时间为600秒
                  driver.set_sleep_time(600)
        """
        return self._driver_impl.set_sleep_time(sleep_time)

    def restore_sleep_time(self):
        """
        @func: 恢复设置应用中设置的熄屏时间。注意需要先调用driver.set_sleep_time后该接口才能正常调用，否则
               会执行失败。
        @example: # 设置熄屏时间为600秒
                  driver.set_sleep_time(600)
                  # 恢复设置应用中设置的熄屏时间
                  driver.restore_sleep_time()
        """
        return self._driver_impl.restore_sleep_time()

    def add_hook(self, hook_type, hook_id, callback):
        """
        @func: 添加操作事件钩子
        @param hook_type: 钩子函数触发的事件类型, 当前仅支持EventManager.EVENT_UI_ACTION_START, 该钩子函数会在框架进行设备操作前触发
        @param hook_id: 钩子函数自定义id, 每个id对应一个钩子函数, 相同的id会覆盖已有的钩子函数, 不同的id可以设置多个钩子函数
        @param callback: 钩子函数, 函数签名为callback(event_type: str, param: dict)
        @example: from hypium.utils.event_manager import EventManager
                  # 为EventManager.EVENT_UI_ACTION_START事件添加一个钩子函数print_test, 钩子函数id为id为perf_hook
                  driver.add_hook(EventManager.EVENT_UI_ACTION_START, "perf_hook", print_test)
        """
        self._driver_impl.add_hook(hook_type, hook_id, callback)

    def remove_hook(self, hook_type, hook_id):
        """
        @func: 移除操作事件钩子
        @param hook_type: 钩子函数触发的事件类型, 当前仅支持EventManager.EVENT_UI_ACTION_START, 该钩子函数会在框架进行设备操作前触发
        @param hook_id: 钩子函数自定义id, 每个id对应一个钩子函数
        @example: from hypium.utils.event_manager import EventManager
                  # 移除EventManager.EVENT_UI_ACTION_START事件中id为perf_hook的钩子
                  driver.remove_hook(EventManager.EVENT_UI_ACTION_START, "perf_hook")
        """
        self._driver_impl.remove_hook(hook_type, hook_id)

    def remove_all_hooks(self, hook_type):
        """
        @func 移除指定事件的所有钩子
        @param hook_type: 钩子函数触发的事件类型
        @example: from hypium.utils.event_manager import EventManager
                  # 移除EventManager.EVENT_UI_ACTION_START事件的所有钩子
                  driver.remove_all_hooks(EventManager.EVENT_UI_ACTION_START)
        """
        self._driver_impl.remove_all_hooks(hook_type)

    @classmethod
    def connect(cls, connector="hdc", **kwargs) -> 'UiDriver':
        """
        @func 在非hypium用例类中快速创建driver, hypium用例类中请使用UiDriver(self.device1)创建UiDriver
              默认连接第一可用的设备
        @param connector: 设备连接模式, 当前仅支持hdc
        @param kwargs: 其他配置参数, 当前支持
                        device_sn: 指定连接的设备sn号, 不指定则使用hdc读取的第一个设备
                        report_path: 指定driver落盘日志保存目录, 默认为工作目录reports下当前时间命名的目录, 不存在会自动创建
                                     如果指定目录，则日志保存到指定目录中，指定目录必须存在
                        log_level: 指定打印日志级别, 默认info -- 当前支持info/debug
                        connector_server: 远程设备服务器地址, 格式为(ip, port), 在连接远程hdc server时使用。
        @example: # 连接默认设备
                  driver = UiDriver.connect()
                  # 连接指定设备
                  driver = UiDriver.connect(device_sn="xxxxxx")
                  # 自定义落盘日志目录
                  driver = UiDriver.connect(report_path="tmp")
                  # 开启debug日志
                  driver = UiDriver.connect(log_level="debug")
                  # 连接远程设备
                  driver = UiDriver.connect(connector_server=("10.176.11.11", 8710))
                  # 注意结束driver使用后需要调用driver.close清理端口, 释放资源
                  driver.close()
        """
        device = device_connector.connect_device(connector, **kwargs)
        return cls(device, **kwargs)

    def close(self):
        """
        @func 关闭驱动, 断开与设备的连接并清理连接资源。
              仅当使用UiDriver.connect方式创建设备驱动，并且驱动对象不再使用时调用。
              如果在Hypium框架用例工程中创建驱动则无需主动调用，任务直接结束会自动完成释放。
        @example:
              # 通过UiDriver.connect方式连接
              driver = UiDriver.connect()
              # 调用driver执行操作
              driver.go_home()
              # 不再使用driver时关闭
              driver.close()
        """
        self._driver_impl.close()
        Tracker.upload()

    def __init__(self, device, agent_mode: str = 'auto', **kwargs):
        """
        根据设备类型, 创建不同系统的driver实现对象, 传入device设备对象创建driver
        """
        self._driver_impl = device_connector.create_driver_impl(device, agent_mode, **kwargs)
        self._driver_impl.log.info("hypium base version: %s" % __version__)
        setattr(self._driver_impl.driver, constant.FULL_DRIVER_TMP_KEY, weakref.proxy(self))

    def __getattr__(self, item):
        warnings.warn(f"try to call deprecated or unknown method [{item}]", DeprecationWarning)
        attr = getattr(self._driver_impl, item, None)
        if attr is None:
            raise AttributeError(f"UiDriver has no attribute [{item}]")
        return attr

    @property
    def _device(self):
        return getattr(self._driver_impl, "_device", None)

    @property
    def device_sn(self):
        """
        @func 读取设备的sn号
        @example: driver.device_sn
        """
        return getattr(self._driver_impl, "device_sn", "unknown")

    @property
    def log(self) -> ILog:
        """
        @func 日志模块, 支持打印记录到用例报告中的日志
        @example:   # 打印info级别日志
                    driver.log.info("info")
                    # 打印debug级别日志
                    driver.log.debug("debug")
                    # 打印warning级别日志
                    driver.log.warning("warning")
                    # 打印error级别的日志
                    driver.log.error("error")
        """
        return getattr(self._driver_impl, "log")

    @property
    def config(self) -> DriverConfig:
        return getattr(self._driver_impl, "config")

    def get_implicit_wait_time(self) -> float:
        return self._driver_impl.get_implicit_wait_time()

    def get_device_type(self) -> str:
        """
        @func 读取设备类型
        """
        return self._driver_impl.get_device_type()

    def get_os_type(self) -> str:
        return self._driver_impl.get_os_type()

    def set_implicit_wait_time(self, wait_time: float):
        """
        @func:    设置操作控件类的接口在控件未出现时等待的超时时间
        @param:   wait_time: 操作控件类的接口在控件未出现时等待的时间
        @example: driver.set_implicit_wait_time(10)
        """
        return self._driver_impl.set_implicit_wait_time(wait_time)

    @keyword
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
        return self._driver_impl.hdc(cmd, timeout)

    @keyword
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
        return self._driver_impl.shell(cmd, timeout)

    @keyword
    def pull_file(self, device_path: str, local_path: str = None, timeout: int = 60):
        """
        @func:     从设备端的传输文件到pc端
        @param:    device_path: 设备侧保存文件的路径
        @param:    local_path: PC侧保存文件的路
        @param:   timeout: 拉取文件超时时间, 默认60秒
        @example: # 从设备中拉取文件"/data/local/tmp/test.log"保存到pc端的test.log
                  driver.pull_file("/data/local/tmp/test.log", "test.log")
        """
        return self._driver_impl.pull_file(device_path, local_path, timeout)

    @keyword
    def push_file(self, local_path: str, device_path: str, timeout: int = 60):
        """
        @func:   从pc端传输文件到设备端
        @param:  local_path: PC侧文件的路径
        @param:  device_path: 设备侧文件的路径
        @param:  timeout: 推送文件超时时间
        @example:  # 从设备中推送文件test.hap保存到设备端的"/data/local/tmp/test.hap"
                   driver.push_file("test.hap", "/data/local/tmp/test.hap")
        """
        return self._driver_impl.push_file(local_path, device_path, timeout)

    def has_file(self, file_path: str) -> bool:
        """
        @func   查询设备中是否有存在路径为file_path的文件
        @param   file_path: 需要检查的设备端文件路径
        @example # 查询设备端是否存在文件/data/local/tmp/test_file.txt
                 driver.has_file("/data/local/tmp/test_file.txt")
        """
        return self._driver_impl.has_file(file_path)

    @keyword
    def wait(self, wait_time: float):
        """
        @func: 等待wait_time秒
        @param: wait_time: 等待秒数
        @example: # 等待5秒钟
                  driver.wait(5)
        """
        return self._driver_impl.wait(wait_time)

    @keyword
    def start_app(self, package_name: str, page_name: str = None, params: str = "", wait_time: float = 1):
        """
        @func           根据包名启动指定的app
        @param          package_name: 应用程序包名(bundle_name)
        @param          page_name: 应用内页面名称(ability_name)
        @param          params: 其他传递给aa命令行参数
        @param          wait_time: 发送启动指令后，等待app启动的时间
        @example        # 启动包名为com.huawei.hmos.browser应用的MainAbility
                        driver.start_app("com.huawei.hmos.browser", "MainAbility")
        """
        return self._driver_impl.start_app(package_name, page_name, params, wait_time)

    @keyword
    def stop_app(self, package_name: str, wait_time: float = 0.5):
        """
        @func      停止指定的应用
        @param     package_name: 应用程序包名
        @param     wait_time: 停止app后延时等待的时间, 单位为秒
        @example   # 停止包名为com.huawei.hmos.browser的应用
                   driver.stop_app("com.huawei.hmos.browser")
        
        """
        return self._driver_impl.stop_app(package_name, wait_time)

    def has_app(self, package_name: str) -> bool:
        """
        @func 查询是否安装指定包名的app
        @param package_name: 需要检查的应用程序包名
        @example: has_app = driver.has_app("com.huawei.hmos.settings")
        """
        return self._driver_impl.has_app(package_name)

    @keyword
    def current_app(self) -> (str, str):
        """
        @func 获取当前前台运行的app信息
        @return app包名和页面名称, 例如('com.huawei.hmos.settings', 'com.huawei.hmos.settings.MainAbility'),
                如果读取失败则返回(None, None)
        @example: package_name, page_name = driver.current_app()
        """
        return self._driver_impl.current_app()

    @keyword
    def install_app(self, package_path: str, options: str = "", **kwargs):
        """
        @func 安装app
        @param package_path: PC端保存的安装包路径
        @param options: 传递给install命令的额外参数
        @example  # 安装路径为test.hap的安装包到手机
                  driver.install_app(r"test.hap")
                  # 替换安装路径为test.hap的安装包到手机(增加-r参数指定替换安装)
                  driver.install_app(r"test.hap", "-r")
        
        """
        return self._driver_impl.install_app(package_path, options, **kwargs)

    @keyword
    def uninstall_app(self, package_name: str, **kwargs):
        """
        @func 卸载App
        @param package_name: 需要卸载的app包名
        @example driver.uninstall_app("com.ohos.devicetest")
        """
        return self._driver_impl.uninstall_app(package_name, **kwargs)

    @keyword
    def clear_app_data(self, package_name: str):
        """
        @func 清除app的数据
        @param package_name: app包名，对应Openharmony中的bundle name
        @example # 清除包名为com.tencent.mm的应用的所有数据
                 driver.clear_app_data("com.tencent.mm")
        """
        return self._driver_impl.clear_app_data(package_name)

    @keyword
    def wake_up_display(self):
        """
        @func 唤醒屏幕
        @example # 唤醒屏幕
                 driver.wake_up_display()
        """
        return self._driver_impl.wake_up_display()

    @keyword
    def get_display_rotation(self) -> DisplayRotation:
        """
        @func: 获取当前设备的屏幕显示方向
        @example # 获取当前设备的屏幕显示方向
                 display_rotation = driver.get_display_rotation()
        """
        return self._driver_impl.get_display_rotation()

    @keyword
    def set_display_rotation(self, rotation: DisplayRotation):
        """
        @func: 将设备的屏幕显示方向设置为指定的显示方向。注意部分应用不支持旋转，该接口设置的旋转方向在
               此类应用上不会生效
        @param rotation: 屏幕旋转方向, 取值范围为DisplayRotation枚举值。
        @example: # 顺时针选择90度
                  driver.set_display_rotation(DisplayRotation.ROTATION_90)
                  # 顺时针选择180度
                  driver.set_display_rotation(DisplayRotation.ROTATION_180)
        """
        return self._driver_impl.set_display_rotation(rotation)

    @keyword
    def set_display_rotation_enabled(self, enabled: bool):
        """
        @func: 启用/禁用设备旋转屏幕的功能
        @param enabled: 能否旋转屏幕的标识
        @example # 设置开启/关闭设备自动旋转。
             driver.set_display_rotation_enabled(True)
             driver.set_display_rotation_enabled(False)
        """
        return self._driver_impl.set_display_rotation_enabled(enabled)

    @keyword
    @record_action
    def drag(self, start: Union[ISelector, tuple, IUiComponent], end: Union[ISelector, tuple, IUiComponent],
             area: Union[ISelector, IUiComponent] = None, press_time: float = 1.5, drag_time: float = 1,
             speed: int = None):
        """
        @func:       根据指定的起始和结束位置执行拖拽操作，起始和结束的位置可以为控件或者屏幕坐标
        @param:      start: 拖拽起始位置，支持三种类型：
                        1. BY控件选择器
                        2. 控件对象
                        3. 屏幕坐标（通过tuple类型指定，例如(100, 200)， 其中100为x轴坐标，200为y轴坐标，
                                   或相对于区域长度和宽度的比例坐标，例如(0.1, 0.2)。)
        @param:      end: 拖拽结束位置
                        1. BY控件选择器
                        2. 控件对象
                        3. 屏幕坐标（通过tuple类型指定，例如(100, 200)， 其中100为x轴坐标，200为y轴坐标，
                                   或者相对于区域长度和宽度的比例坐标，例如(0.1, 0.2)。)
        @param:      area: 拖拽操作区域，可以为控件BY.text("画布"), 或者使用find_component找到的控件对象。
                           目前仅在start或者end为坐标时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域
                           的相对位置坐标。
        @param:      press_time: 拖拽操作开始时，长按的时间, 默认为1.5s。 该参数仅设备API level >= 20时支持设置。
        @param:      drag_time: 拖动的时间， 默认为1s(整个拖拽操作总时间 = press_time + drag_time)
        @param:      speed: 拖拽速度, 指定速度时, drag_time不生效
        @example:    # 拖拽文本为"文件.txt"的控件到文本为"上传文件"的控件
                     driver.drag(BY.text("文件.txt"), BY.text("上传文件"))
                     # 拖拽id为"start_bar"的控件到坐标(100, 200)的位置, 拖拽时间为2秒
                     driver.drag(BY.key("start_bar"), (100, 200), drag_time=2)

                     # 在id为"Canvas"的控件上执行拖拽操作，从"Canvas"控件中(0.1， 0.5)的位置拖拽到(0.9, 0.5)位置。
                     # 假如"Canvas"控件左上角坐标(100, 100), 宽度为200，高度为50，此操作等价于
                     # driver.drag((100 + 0.1 * 200, 100 + 0.5 * 50), (100 + 0.9 * 200, 100 + 0.5 * 50))
                     driver.drag((0.1, 0.5), (0.9, 0.5), area=BY.id("Canvas"))

                     # 在滑动条上执行拖拽操作, 以滑动条组件左上角为原点, 从滑动条区域中的(10, 10)拖拽到(10, 200)。
                     # 假设滑动条左上角坐标为(500, 500), 此操作等价于driver.drag((500 + 10, 500 + 10), (500 + 10, 500 + 200))
                     driver.drag((10, 10), (10, 200), area=BY.type("Slider"))
        """
        return self._driver_impl.drag(start, end, area, press_time, drag_time, speed)

    @keyword
    @record_action
    def touch(self, target: Union[ISelector, IUiComponent, tuple], mode: str = "normal",
              scroll_target: Union[ISelector, IUiComponent] = None, wait_time: float = 0.1,
              offset: tuple = None):
        """
        @func:    根据选定的控件或者坐标位置执行点击操作
        @param:   target: 需要点击的目标，可以为控件(通过By类指定)或者屏幕坐标(通过tuple类型指定，
                         例如(100, 200)， 其中100为x轴坐标，200为y轴坐标), 或者使用find_component找到的控件对象
        @param:   mode: 点击模式，目前支持:
                       "normal" 点击
                       "long" 长按（长按后放开）
                       "double" 双击
        @param:   scroll_target: 指定可滚动的控件，在该控件中滚动搜索指定的目标控件target。仅在
                                target为`By`对象时有效
        @param:   wait_time: 点击后等待响应的时间，默认0.1s
        @param:   offset: 点击坐标相对目标控件的偏移, 例如(0.5, 0.5)表示点击目标中心, (0, 0)表示左上角, (1, 1)表示右下角
                          支持负数, 每个方向的偏移值取值范围为[-1, 1]
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
                  # 长按比例坐标为(0.8, 0.9)的位置
                  driver.touch((0.8, 0.9), mode="long")
        """
        return self._driver_impl.touch(target, mode, scroll_target, wait_time, offset)

    @keyword
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
        return self._driver_impl.find_image(image_path_pc, mode, **kwargs)

    @keyword
    @record_action
    def touch_image(self, image_path_pc: str, mode: str = "normal", similarity: float = 0.95, wait_time: int = 0.1,
                    **kwargs):
        """
        @func:    在屏幕上显示内容同图片image_path_pc内容相同的位置执行点击操作， 注意模板图片分辨率需与屏幕目标区域一致，
                  如果图片被缩放或旋转将无法正常匹配到正确的位置。
        @param:   image_path_pc: 需要点击的图像的存储路径(图片存储在PC端)
        @param:   mode: 点击模式，目前支持:
                       "normal" 点击
                       "long" 长按（长按后放开）
                       "double" 双击
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
        return self._driver_impl.touch_image(image_path_pc, mode, similarity, wait_time, **kwargs)

    @keyword
    @record_action
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
        return self._driver_impl.switch_component_status(component, checked)

    @keyword
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
        return self._driver_impl.press_combination_key(key1, key2, key3)

    @keyword
    def press_key(self, key_code: Union[KeyCode, int], key_code2: Union[KeyCode, int] = None, mode="normal"):
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
        return self._driver_impl.press_key(key_code, key_code2, mode)

    @keyword
    def press_home(self):
        """
        @func 按下HOME键
        @example: # 按下home键
                  driver.press_home()
        """
        return self._driver_impl.press_home()

    @keyword
    def go_home(self):
        """
        @func 返回桌面(不关心返回桌面的方式，自动决定最稳定的返回桌面方式)
        @example: # 返回桌面
                  driver.go_home()
        """
        return self._driver_impl.go_home()

    @keyword
    def go_back(self):
        """
        @func 返回上一级(不关心返回桌面的方式，自动决定最稳定的返回方式)
        @example: # 返回桌面
                  driver.go_back()
        """
        return self._driver_impl.go_back()

    @keyword
    def press_power(self):
        """
        @func 按下电源键
        @example: # 按下电源键
                  driver.press_power()
        """
        return self._driver_impl.press_power()

    @keyword
    @record_action
    def get_component_bound(self, component: Union[ISelector, IUiComponent]) -> Rect:
        """
        @func 获取指定的控件的边界矩形区域
        @param: component: 需要获取边框位置的控件选择器或者控件对象
        @return: 返回控件边界坐标的Rect对象，如果没找到控件则返回None
        @example # 获取text为按钮的控件的边框位置
                 bounds = driver.get_component_bound(BY.text("按钮"))
                 # 获取控件对象的边框位置
                 component = driver.find_component(BY.text("按钮"))
                 bounds = driver.get_component_bound(component)
        """
        return self._driver_impl.get_component_bound(component)

    @keyword
    def press_back(self):
        """
        @func 按下返回键
        @example: # 按下返回键
                  driver.press_back()
        """
        return self._driver_impl.press_back()

    @keyword
    @record_action
    def slide(self, start: Union[ISelector, tuple], end: Union[ISelector, tuple],
              area: Union[ISelector, IUiComponent] = None,
              slide_time: float = DEFAULT_SLIDE_TIME):
        """
        @func:       根据指定的起始和结束位置执行滑动操作，起始和结束的位置可以为控件或者屏幕坐标。该接口用于执行较为精准的滑动操作。
        @param:      start: 滑动起始位置，可以为控件BY.text("滑块")或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      end: 滑动结束位置，可以为控件BY.text("最大值")或者坐标(100, 200), 或者使用find_component找到的控件对象
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
                     driver.slide((0, 0), (100, 0), area = BY.type("Slider"))
        """
        return self._driver_impl.slide(start, end, area, slide_time)

    @keyword
    @record_action
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
                              这样的比例坐标。当同时传入side和start_point的时候,
        @param   swipe_time: 滑动时间（s)， 默认0.3s
        @param:  speed: 滑动速度, 单位像素/秒, 指定速度时, swipe_time不生效
        @example    # 在屏幕上向上滑动, 距离40
                    driver.swipe(UiParam.UP, distance=40)
                    # 在屏幕上向右滑动, 滑动时间为0.1秒
                    driver.swipe(UiParam.RIGHT, swipe_time=0.1)
                    # 在屏幕起始点为比例坐标为(0.8, 0.8)的位置向上滑动，距离30
                    driver.swipe(UiParam.UP, 30, start_point=(0.8, 0.8))
                    # 在屏幕左边区域向下滑动， 距离30
                    driver.swipe(UiParam.DOWN, 30, side=UiParam.LEFT)
                    # 在屏幕右侧区域向上滑动，距离30
                    driver.swipe(UiParam.UP, side=UiParam.RIGHT)
                    # 在类型为Scroll的控件中向上滑动
                    driver.swipe(UiParam.UP, area=BY.type("Scroll"))
        """
        return self._driver_impl.swipe(direction, distance, area, side, start_point, swipe_time, speed)

    @keyword
    def find_component(self, target: ISelector, scroll_target: ISelector = None) -> IUiComponent:
        """
        @func 根据BY指定的条件查找控件, 返回满足条件的第一个控件对象
        @param target: 使用By对象描述的查找条件
        @param scroll_target: 滑动scroll_target控件, 搜索target
        @return 返回控件对象IUiComponent, 如果没有找到满足条件的控件，则返回None
        @example # 查找类型为button的第一个控件对象
                 component = driver.find_component(BY.type("button"))
                 # 获取控件对象的文本
                 text = component.getText()
                 # 在类型为Scroll的控件上滚动查找文本为"拒绝"的控件
                 component = driver.find_component(BY.text("拒绝"), scroll_target=BY.type("Scroll"))
        """
        return self._driver_impl.find_component(target, scroll_target)

    @keyword
    def find_all_components(self, target: ISelector, index: int = None) -> Union[IUiComponent, List[IUiComponent]]:
        """
        @func 根据BY指定的条件查找控件, 返回满足条件的所有控件对象列表, 或者列表中第index个控件对象
        @param target: 使用By对象描述的查找条件
        @param index 默认为None, 表示返回所有控件列表，当传入整数时, 返回列表中第index个对象
        @return 返回控件对象IUiComponent或者控件对象列表, 例如[component1, component2], 每个
                如果没有找到满足条件的控件，则返回None
        @example # 查找所有类型为"button"的控件
                 components = driver.find_all_components(BY.type("Button"))
                 # 查找满足条件的第3个控件(index从0开始)
                 component = driver.find_all_components(BY.type("Button"), 2)
                 # 点击控件
                 driver.touch(component)
        """
        return self._driver_impl.find_all_components(target, index)

    @keyword
    def find_window(self, filter: WindowFilter) -> UiWindow:
        """
        @func 根据指定条件查找窗口, 返回窗口对象
        @param filter: 使用WindowFilter对象指定查找条件
        @return 如果找到window则返回UiWindow对象, 否则返回None
        @example: # 查找标题为日历的窗口
                  window = driver.find_window(WindowFilter().title("日历"))
                  # 查找包名为com.huawei.hmos.settings，并且处于活动状态的窗口
                  window = driver.find_window(WindowFilter().bundle_name("com.huawei.hmos.settings").actived(True))
                  # 查找处于活动状态的窗口
                  window = driver.find_window(WindowFilter().actived(True))
                  # 查找聚焦状态的窗口
                  window = driver.find_window(WindowFilter().focused(True))
        """
        return self._driver_impl.find_window(filter)

    @keyword
    def get_display_size(self) -> (int, int):
        """
        @func 返回屏幕分辨率
        @return (宽度, 高度)
        @example: # 获取屏幕分辨率
                  width, height = driver.get_display_size()
        """
        return self._driver_impl.get_display_size()

    @keyword
    def get_window_size(self) -> (int, int):
        """
        @func 获取当前处于活动状态的窗口大小
        @return (宽度, 高度), 如果不存在活动/获焦的窗口则返回None
        @example: # 获取当前活动状态的窗口大小
                  width, height = driver.get_window_size()
        """
        return self._driver_impl.get_window_size()

    @keyword
    def get_current_window(self) -> UiWindow:
        """
        @func 返回当前用户正在操作的窗口(处于活动或者获焦状态的窗口对)
        @return 窗口对象，如果不存在活动或者获焦的窗口，则返回None
        @example # 获取当前活动的窗口对象
                 window = driver.get_current_window()
                 # 读取窗口所属的应用包名
                 bundle_name = window.getBundleName()
                 # 读取窗口边框
                 bounds = window.getBounds()
        """
        return self._driver_impl.get_current_window()

    @record_action
    def get_component_property(self, component: Union[ISelector, IUiComponent], property_name: str) -> Any:
        """
        @func 获取指定控件属性
        @param component: By对象指定的控件或者IUiComponent控件对象
        @param property_name: 属性名称, 目前支持:
                              "id", "text", "key", "type", "enabled", "focused", "clickable", "scrollable"
                              "checked", "checkable"
        @return: 指定控件的指定属性值
        @example: # 获取类型为"checkbox"的控件的checked状态
                  checked = driver.get_component_property(BY.type("Toggle"), "checked")
                  # 获取id为"text_container"的控件的文本属性
                  text = driver.get_component_property(BY.key("text_container"), "text")
        """
        return self._driver_impl.get_component_property(component, property_name)

    def capture_screen(self, save_path: str, in_pc: bool = True,
                       area: Union[Rect, ISelector, IUiComponent] = None) -> str:
        """
        @func 通过系统命令获取屏幕截图的图片, 并保存到设备或者PC上指定位置
        @param save_path: 截图保存路径(目录 + 文件名)
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
        return self._driver_impl.capture_screen(save_path, in_pc, area)

    @keyword
    def take_screenshot(self, mode: str = "key"):
        """
        @func 模拟用户触发系统截屏的操作, 例如通过按音量下键+电源键
        @param mode: 进行系统截屏的方式，当前支持
                     "key" 例如通过按音量下键+电源键
                     默认通过按音量下键+电源键实现
        @example: # 模拟用户执行截屏操作
                  driver.take_screenshot()
        """
        return self._driver_impl.take_screenshot(mode)

    @keyword
    def input_text(self, component: Union[ISelector, IUiComponent, tuple], text: str, mode: InputTextMode = None):
        """
        @func 向指定控件中输入文本内容
        @param component: 需要输入文本的控件，可以使用ISelector对象，
                          或者使用find_component找到的控件对象,
                          以及坐标点(x, y)
        @param text: 需要输入的文本
        @param mode: 输入模式配置(该参数需要设备API level >= 20支持), 默认模式如下:
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
        return self._driver_impl.input_text(component, text, mode)

    @keyword
    def clear_text(self, component: Union[ISelector, IUiComponent]):
        """
        @func 清空指定控件中的文本内容
        @param component: 需要清除文本的控件
        @example: # 清除类型为"InputText"的控件中的内容
                  driver.clear_text(BY.type("InputText"))
        """
        return self._driver_impl.clear_text(component)

    @keyword
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
        return self._driver_impl.move_cursor(direction, times)

    @keyword
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
        return self._driver_impl.wait_for_idle(idle_time, timeout)

    @keyword
    def wait_for_component(self, by: ISelector, timeout: float = DEFAULT_TIMEOUT) -> IUiComponent:
        """
        @func 等待目标控件出现, 如果出现则返回控件对象
        @param by: 等待出现的控件, 通过By类指定
        @param timeout: 等待超时时间, 单位秒
        @return: 控件在超时前出现则返回IUiComponent控件对象，否则返回None
        @example # 等待id为"confirm_button"的控件出现，超时时间为10秒
                 driver.wait_for_component(BY.key("confirm_button"), timeout=10)
                 # 等待id为"confirm_button"的控件出现
                 driver.wait_for_component(BY.key("confirm_button"))
        """
        return self._driver_impl.wait_for_component(by, timeout)

    @keyword
    def wait_for_component_disappear(self, by: ISelector, timeout: float = DEFAULT_TIMEOUT):
        """
        @func 等待控件消失
        @param by: 等待消失的控件, 通过By类指定
        @param timeout: 等待超时时间, 单位秒
        @example # 等待id为"confirm_button"的控件消失，超时时间为10秒
                 driver.wait_for_component_disappear(BY.key("confirm_button"), timeout=10)
        @return None表示控件消失, 否则返回控件对象IUiComponent表示等待超时控件仍未消失
        """
        return self._driver_impl.wait_for_component_disappear(by, timeout)

    @keyword
    def to_abs_pos(self, x: float, y: float) -> (int, int):
        """
        @func 根据屏幕分辨率将比例坐标转换为绝对坐标
        @param x 相对x坐标，范围0~1
        @param y 相对y坐标，范围0~1
        @example # 将比例坐标(0.1, 0.8)转为屏幕上的绝对坐标
                 abs_pos = driver.to_abs_pos(0.1, 0.8)
        @return: 比例坐标对应的绝对坐标
        """
        return self._driver_impl.to_abs_pos(x, y)

    @keyword
    def pinch_in(self, area: Union[ISelector, IUiComponent, Rect], scale: float = 0.4, direction: str = "diagonal",
                 **kwargs):
        """
        @func 在控件上捏合缩小
        @param area: 手势执行的区域
        @param scale: 缩放的比例, [0, 1], 值越小表示缩放操作距离越长, 缩小的越多
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
        return self._driver_impl.pinch_in(area, scale, direction, **kwargs)

    @keyword
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
        @example  # 在类型为Image的控件上进行双指放大操作
                  driver.pinch_out(BY.type("Image"))
                  # 在类型为Image的控件上进行双指捏合缩小操作, 设置水平方向捏合
                  driver.pinch_out(BY.type("Image"), direction="horizontal")
        """
        return self._driver_impl.pinch_out(area, scale, direction, **kwargs)

    @keyword
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
        return self._driver_impl.fling(direction, distance, area, speed)

    @keyword
    def inject_gesture(self, gesture: Gesture, speed: int = 2000):
        """
        @func 执行自定义滑动手势操作
        @param gesture: 描述手势操作的Gesture对象
        @param speed: 默认操作速度, 当生成Gesture对象的某个步骤中没有传入操作时间的默认使用该速度进行操作
        @example:   from hypium import Gesture
                    # 创建一个gesture对象
                    gesture = Gesture()
                    # 获取控件计算器的位置
                    pos = driver.findComponent(BY.text("计算器")).getBoundsCenter()
                    # 获取屏幕尺寸
                    size = driver.getDisplaySize()
                    # 起始位置, 长按2秒
                    gesture.start(pos.to_tuple(), 2)
                    # 移动到屏幕边缘
                    gesture.move_to(Point(size.X - 20, int(size.Y / 2)).to_tuple())
                    # 停留2秒
                    gesture.pause(2)
                    # 移动到(360, 500)的位置
                    gesture.move_to(Point(360, 500).to_tuple())
                    # 停留2秒结束
                    gesture.pause(2)
                    # 执行gesture对象描述的操作
                    driver.inject_gesture(gesture)
        """
        return self._driver_impl.inject_gesture(gesture, speed)

    @keyword
    def mouse_double_click(self, pos: Union[tuple, IUiComponent, ISelector],
                           button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT):
        """
        @func 鼠标双击
        @param pos: 点击的位置, 例如(100, 200)
        @param button_id: 需要点击的鼠标按键
        @example # 使用鼠标左键双击(100, 200)的位置
                 driver.mouse_double_click((100, 200), MouseButton.MOUSE_BUTTON_LEFT)
                 # 使用鼠标右键双击文本为"确认"
                 driver.mouse_double_click(BY.text("确认"), MouseButton.MOUSE_BUTTON_RIGHT)
        """
        return self._driver_impl.mouse_double_click(pos, button_id)

    @keyword
    def mouse_long_click(self, pos: Union[tuple, IUiComponent, ISelector],
                         button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT, press_time: float = 1.5):
        """
        @func 鼠标长按(rk板测试未生效)
        @param pos: 长按的位置, 例如(100, 200)
        @param button_id: 需要点击的鼠标按键
        @param press_time: 长按的时间
        @example # 使用鼠标左键长按(100, 200)的位置
                 driver.mouse_long_click((100, 200), MouseButton.MOUSE_BUTTON_LEFT)
                 # 使用鼠标右键长按文本为"确认"的控件
                 driver.mouse_long_click(BY.text("确认"), MouseButton.MOUSE_BUTTON_RIGHT)
                 # 使用鼠标右键长按比例坐标(0.8, 0.5)的位置
                 driver.mouse_long_click((0.8, 0.5), MouseButton.MOUSE_BUTTON_RIGHT)
        """
        return self._driver_impl.mouse_long_click(pos, button_id, press_time)

    @keyword
    def mouse_click(self, pos: Union[tuple, IUiComponent, ISelector],
                    button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT,
                    key1: Union[KeyCode, int] = None, key2: Union[KeyCode, int] = None):
        """
        @func 鼠标点击, 支持键鼠组合操作
        @param pos: 点击的位置, 支持位置, IUiComponent对象以及By, 例如(100, 200), BY.text("确认")
        @param button_id: 需要点击的鼠标按键
        @param key1:  需要组合按下的第一个键盘按键
        @param key2: 需要组合按下的第二个键盘按键
        @example # 使用鼠标左键点击(100, 200)的位置
                 driver.mouse_long_click((100, 200), MouseButton.MOUSE_BUTTON_LEFT)
                 # 使用鼠标右键点击文本为"确认"的控件
                 driver.mouse_long_click(BY.text("确认"), MouseButton.MOUSE_BUTTON_RIGHT)
                 # 使用鼠标右键点击比例坐标(0.8, 0.5)的位置
                 driver.mouse_long_click((0.8, 0.5), MouseButton.MOUSE_BUTTON_RIGHT)
        """
        return self._driver_impl.mouse_click(pos, button_id, key1, key2)

    @keyword
    def mouse_scroll(self, pos: Union[tuple, IUiComponent, ISelector], scroll_direction: str, scroll_steps: int,
                     key1: int = None, key2: int = None, **kwargs):
        """
        @func 鼠标滚动, 支持键鼠组合操作
        @param pos: 滚动的位置, 例如(100, 200)
        @param scroll_direction: 滚动方向
                                 "up" 向上滚动
                                 "down" 向下滚动
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
        return self._driver_impl.mouse_scroll(pos, scroll_direction, scroll_steps, key1, key2, **kwargs)

    @keyword
    def mouse_move_to(self, pos: Union[tuple, IUiComponent, ISelector]):
        """
        @func 鼠标指针移动到指定位置
        @param pos: 鼠标指针的位置, 例如(100, 200)
        @example # 鼠标移动到(100, 200)的位置
                 driver.mouse_move_to((100, 200))
                 # 鼠标移动到文本为"查看"的控件
                 driver.mouse_move_to(BY.text("查看"))
                 # 鼠标移动到比例坐标(0.8, 0.5)的位置
                 driver.mouse_long_click((0.8, 0.5))
        """
        return self._driver_impl.mouse_move_to(pos)

    @keyword
    def mouse_move(self, start: Union[tuple, IUiComponent, ISelector], end: Union[tuple, IUiComponent, ISelector],
                   speed: int = 3000):
        """
        @func 鼠标指针从之前起始位置移动到结束位置，模拟移动轨迹和速度
        @param start: 起始位置, 支持坐标和控件
        @param end: 结束位置, 支持坐标和控件
        @param speed: 鼠标移动速度，像素/秒
        @example: # 鼠标从控件1移动到控件2
                  driver.mouse_move(BY.text("控件1"), BY.text("控件2"))
        """
        return self._driver_impl.mouse_move(start, end, speed)

    @keyword
    def mouse_drag(self, start: Union[tuple, IUiComponent, ISelector], end: Union[tuple, IUiComponent, ISelector],
                   speed: int = 3000):
        """
        @func 使用鼠标进行拖拽操作(按住鼠标左键移动鼠标)
        @param start: 起始位置, 支持坐标和控件
        @param end: 结束位置, 支持坐标和控件
        @param speed: 鼠标移动速度，像素/秒
        @example: # 鼠标从控件1拖拽到控件2
                  driver.mouse_drag(BY.text("控件1"), BY.text("控件2"))
        """
        return self._driver_impl.mouse_drag(start, end, speed)

    @keyword
    def swipe_to_home(self, times: int = 1):
        """
        @func 屏幕低端上滑回到桌面
        @precondition 设备开启触摸屏手势导航
        @param times: 上滑次数, 默认1次, 某些场景可能需要两次上滑才能返回桌面
        @example # 上滑返回桌面
                 driver.swipe_to_home()
                 # 连续上滑2次返回桌面
                 driver.swipe_to_home(times=2)
        """
        return self._driver_impl.swipe_to_home(times)

    @keyword
    def swipe_to_back(self, side=UiParam.RIGHT, times: int = 1, height: float = 0.5):
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
                 driver.swipe_to_back(height=0.8)
        """
        return self._driver_impl.swipe_to_back(side, times, height)

    @keyword
    def swipe_to_recent_task(self):
        """
        @func 屏幕底端上滑停顿, 打开多任务界面
        @precondition 设备开启触摸屏手势导航
        @example: # 上滑停顿进度多任务界面
                  driver.swipe_to_recent_task()
        """
        return self._driver_impl.swipe_to_recent_task()

    @checkepr
    def check_current_window(self, title: str = None, bundle_name: str = None):
        """
        @func:     检查当前活动的窗口的属性是否符合预期
        @param:    title: 预期的窗口标题, None表示不检查
        @param:    bundle_name: 预期窗口所属的app包名, None表示不检查
        @example   # 检查当前活动窗口的标题为"畅连"
                   driver.check_current_window(title="畅连")
                   # 检查当前活动窗口对应的应用包名为"com.huawei.hmos.settings"
                   driver.check_current_window(bundle_name="com.huawei.hmos.settings")
        """
        return self._driver_impl.check_current_window(title, bundle_name)

    @checkepr
    def check_window(self, window: WindowFilter, title: str = None, bundle_name: str = None):
        """
        @func:     检查指定的window的属性是否符合预期
        @param:    title: 预期的窗口标题, None表示不检查
        @param:    bundle_name: 预期窗口所属的app包名, None表示不检查
        @example   # 检查当前焦点窗口的包名为com.huawei.hmos.settings
                   driver.check_window(WindowFilter().focused(True), bundle_name="com.huawei.hmos.settings")
        """
        return self._driver_impl.check_window(window, title, bundle_name)

    @checkepr
    def check_component_exist(self, component: ISelector, expect_exist: bool = True, wait_time: int = 0,
                              scroll_target: Union[ISelector, IUiComponent] = None):
        """
        @func:     检查指定UI控件是否存在
        @param:    component: 待检查的UI控件, 使用By对象指定
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
        return self._driver_impl.check_component_exist(component, expect_exist, wait_time, scroll_target)

    @checkepr
    def check_component(self, component: Union[ISelector, IUiComponent], expected_equal: bool = True, **kwargs):
        """
        @func 检查控件属性是否符合预期
        @param component: 需要检查的控件, 支持By或者IUiComponent对象
        @param expected_equal: 预期值和实际值是否相等，True表示预期相等，False表示预期不相等
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
        return self._driver_impl.check_component(component, expected_equal, **kwargs)

    @checkepr
    def check_window_exist(self, window: WindowFilter, expect_exist: bool = True):
        """
        @func:     检查指定的window是否存在
        @param:    window: 待检查的窗口选择器
        @param:    expect_exist: 是否期望窗口存在, True表示期望窗口存在，False表示期望窗口不存在
        @example:  # 检查包名为com.huawei.hmos.settings的窗口存在
                   driver.check_window_exist(WindowFilter().bundle_name("com.huawei.hmos.settings"))
                   # 检查标题为畅连的窗口不存在
                   driver.check_window_exist(WindowFilter().title("畅联"), expect_exist=False)
                   # 检查包名为com.huawei.hmos.settings, 标题为设置的窗口存在
                   driver.check_window_exist(WindowFilter().title("设置").bundle_name("com.huawei.hmos.settings"))
        """
        return self._driver_impl.check_window_exist(window, expect_exist)

    @checkepr
    def check_image_exist(self, image_path_pc: str, expect_exist: bool = True, similarity: float = 0.95,
                          timeout: int = 3, mode="template", **kwargs):
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
        return self._driver_impl.check_image_exist(image_path_pc, expect_exist, similarity, timeout, mode, **kwargs)

    @keyword
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
        return self._driver_impl.start_listen_toast()

    @keyword
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
                  text_in_toast = driver.get_latest_toast(timeout=5)
                  # 检查text_in_toast等于发送成功
                  host.check_equal(text_in_toast, "发送成功")
        """
        return self._driver_impl.get_latest_toast(timeout)

    @checkepr
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
                  driver.check_toast("发送成功")
        """
        return self._driver_impl.check_toast(expect_text, fuzzy, timeout)

    @keyword
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
        return self._driver_impl.start_listen_ui_event(event_type)

    @keyword
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
        return self._driver_impl.get_latest_ui_event(timeout)

    @keyword
    def inject_multi_finger_gesture(self, gestures: List[Gesture], speed: int = 2000):
        """
        @func 注入多指手势操作
        @param gestures: 表示单指手势操作的Gesture对象列表，每个Gesture对象描述一个手指的操作轨迹。
                         注意如果各个手势持续时间不同，时间短的手势操作会保持在结束位置，等待所有手势完成后抬起对应手指。
        @param speed: Gesture对象的步骤没有设置执行时间时, 使用该速度计算时间, 单位像素/秒
        @example: # 导入Gesture对象
                  from hypium import Gesture
                  # 创建手指1的手势, 从(0.4, 0.4)的位置移动到(0.2, 0.2)的位置
                  gesture1 = Gesture().start((0.4, 0.4)).move_to((0.2, 0.2), interval=1)
                  # 创建手指2的手势, 从(0.6, 0.6)的位置移动到(0.8, 0.8)的位置
                  gesture2 = Gesture().start((0.6, 0.6)).move_to((0.8, 0.8), interval=1)
                  # 注入多指操作
                  driver.inject_multi_finger_gesture((gesture1, gesture2))

        """
        return self._driver_impl.inject_multi_finger_gesture(gestures, speed)

    @keyword
    def two_finger_swipe(self, start1: tuple, end1: tuple, start2: tuple, end2: tuple,
                         duration: float = 0.5, area: Rect = None):
        """
        @func 执行双指滑动操作
        @param start1: 手指1起始坐标
        @param end1: 手指1起始坐标
        @param start2: 手指2起始坐标
        @param end2: 手指2结束坐标
        @param duration: 滑动操作持续时间
        @param area: 滑动操作的区域, 当起始结束坐标为(0.1, 0.2)等相对比例坐标时生效，默认为操作区域为全屏
        @example: # 执行双指滑动操作, 手指1从(0.4, 0.4)滑动到(0.2, 0.2), 手指2从(0.6, 0.6)滑动到(0.8, 0.8)
                  driver.two_finger_swipe((0.4, 0.4), (0.2, 0.2), (0.6, 0.6), (0.8, 0.8))
                  # 执行双指滑动操作, 手指1从(0.4, 0.4)滑动到(0.2, 0.2), 手指2从(0.6, 0.6)滑动到(0.8, 0.8), 持续时间3秒
                  driver.two_finger_swipe((0.4, 0.4), (0.2, 0.2), (0.6, 0.6), (0.8, 0.8), duration=3)
                  # 查找Image类型控件
                  comp = driver.find_component(BY.type("Image"))
                  # 在指定的控件区域内执行双指滑动(滑动起始/停止坐标为控件区域内的比例坐标)
                  driver.two_finger_swipe((0.4, 0.4), (0.1, 0.1), (0.6, 0.6), (0.9, 0.9), area=comp.getBounds())
        """
        return self._driver_impl.two_finger_swipe(start1, end1, start2, end2, duration, area)

    @keyword
    def multi_finger_touch(self, points: List[tuple], duration: float = 0.1, area: Rect = None):
        """
        @func 执行多指点击操作
        @param points: 需要点击的坐标位置列表，每个坐标对应一个手指, 例如[(0.1, 0.2), (0.3, 0.4)], 最多支持4指点击
        @param duration: 按下/抬起的时间，可实现多指长按操作, 单位秒
        @param area: 点击操作的区域, 当起始结束坐标为(0.1, 0.2)等相对比例坐标时生效，默认为操作区域为全屏
        @example: # 执行多指点击操作, 同时点击屏幕(0.1， 0.2), (0.3, 0.4)的位置
                  driver.multi_finger_touch([(0.1， 0.2), (0.3, 0.4)])
                  # 执行多指点击操作, 设置点击按下时间为1秒
                  driver.multi_finger_touch([(0.1， 0.2), (0.3, 0.4)], duration=2)
                  # 查找Image类型控件
                  comp = driver.find_component(BY.type("Image"))
                  # 在指定的控件区域内执行多指点击(点击坐标为控件区域内的比例坐标)
                  driver.multi_finger_touch([(0.5, 0.5), (0.6, 0.6)], area=comp.getBounds())
        """
        return self._driver_impl.multi_finger_touch(points, duration, area)

    @keyword
    def pen_click(self, target: Union[ISelector, IUiComponent, tuple], offset: tuple = None):
        """
        @func 模拟触控笔点击
        @param target: 点击操作目标
        @param offset: 点击坐标在操作目标中的偏移坐标
        @example: # 触控笔点击蓝牙控件
                  driver.pen_click(BY.text("蓝牙"))
                  # 触控笔点击蓝牙控件左上角(偏移0, 0)
                  driver.pen_click(BY.text("蓝牙"), offset=(0, 0))
                  # 触控笔点击蓝牙控件中偏移为0.8, 0.8的位置
                  driver.pen_click(BY.text("蓝牙"), offset=(0.8, 0.8))
                  # 触控笔点击蓝牙控件正上方, 同蓝牙控件距离为蓝牙控件高度的80%的位置(0.5, -0.8)
                  driver.pen_click(BY.text("蓝牙"), offset=(0.5, -0.8))
        """
        self._driver_impl.pen_click(target, offset)

    @keyword
    def pen_double_click(self, target: Union[ISelector, IUiComponent, tuple], offset: tuple = None):
        """
        @func 模拟触控笔双击
        @param target: 点击操作目标
        @param offset: 点击坐标在操作目标中的偏移坐标
        @example: # 触控笔双击蓝牙控件
                  driver.pen_double_click(BY.text("蓝牙"))
                  # 触控笔双击蓝牙控件左上角(偏移0, 0)
                  driver.pen_double_click(BY.text("蓝牙"), offset=(0, 0))
                  # 触控笔双击蓝牙控件中偏移为0.8, 0.8的位置
                  driver.pen_double_click(BY.text("蓝牙"), offset=(0.8, 0.8))
        """
        self._driver_impl.pen_double_click(target, offset)

    @keyword
    def pen_long_click(self, target: Union[ISelector, IUiComponent, tuple], offset: tuple = None,
                       pressure: float = None):
        """
        @func 模拟触控笔长按
        @param target: 点击操作目标
        @param offset: 点击坐标在操作目标中的偏移坐标
        @param pressure: 触控笔压力值, 范围[0, 1]
        @example: # 触控笔长按蓝牙控件
                  driver.pen_long_click(BY.text("蓝牙"))
                  # 触控笔长按蓝牙控件左上角(偏移0, 0)
                  driver.pen_long_click(BY.text("蓝牙"), offset=(0, 0))
                  # 触控笔长按蓝牙控件中偏移为0.8, 0.8的位置
                  driver.pen_long_click(BY.text("蓝牙"), offset=(0.8, 0.8))
        """
        self._driver_impl.pen_long_click(target, offset, pressure)

    @keyword
    def pen_swipe(self, direction: str, distance: int = 60, start_point: tuple = None,
                  area: Union[ISelector, IUiComponent, Rect] = None, pressure: float = None,
                  duration: float = DEFAULT_SLIDE_TIME, speed: int = None):
        """
        @func    在屏幕上或者指定区域area中执行朝向指定方向direction的触控笔滑动操作。该接口用于执行不太精准的滑动操作。
        @param   direction: 滑动方向，目前支持:
                            "LEFT" 左滑
                            "RIGHT" 右滑
                            "UP" 上滑
                            "DOWN" 下滑
        @param   distance: 相对滑动区域总长度的滑动距离，范围为1-100, 表示滑动长度为滑动区域总长度的1%到100%， 默认为60
        @param   area: 通过控件指定的滑动区域
        @param   start_point: 滑动起始点, 默认为None, 表示在区域中间位置执行滑动操作, 可以传入滑动起始点坐标，支持使用(0.5, 0.5)
                              这样的比例坐标。
        @param   pressure: 触控笔压力值, 范围[0, 1]
        @param   duration: 滑动时长, 单位秒, 默认0.3秒, 同时指定滑动时长和速度时, 仅速度生效
        @param   speed: 滑动速度, 单位px/s, 同时指定滑动时长和速度时, 仅速度生效
        @example    # 在屏幕上向上滑动, 距离40
                    driver.pen_swipe(UiParam.UP, distance=40)
                    # 在屏幕上向右滑动, 滑动时间为0.1秒
                    driver.pen_swipe(UiParam.RIGHT, duration=0.1)
                    # 在屏幕起始点为比例坐标为(0.8, 0.8)的位置向上滑动，距离30
                    driver.pen_swipe(UiParam.UP, 30, start_point=(0.8, 0.8))
                    # 在类型为Scroll的控件中向向滑动
                    driver.pen_swipe(UiParam.UP, area=BY.type("Scroll"))
                    # 在指定区域上滑, 指定速度为3000px/s
                    driver.pen_swipe(UiParam.UP, area=BY.type("Scroll"), speed=3000)
        """
        self._driver_impl.pen_swipe(direction, distance, start_point, area, pressure, duration, speed)

    @keyword
    def pen_slide(self, start: Union[ISelector, IUiComponent, tuple],
                  end: Union[ISelector, IUiComponent, tuple],
                  area: Union[ISelector, IUiComponent, Rect] = None,
                  pressure: float = None,
                  duration: float = DEFAULT_SLIDE_TIME,
                  speed: int = None):
        """
        @func       根据指定的起始和结束位置执行触控笔滑动操作，起始和结束的位置可以为控件或者屏幕坐标。该接口用于执行较为精准的滑动操作。
        @param      start: 滑动起始位置，可以为控件BY.text("滑块")或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param      end: 滑动结束位置，可以为控件BY.text("最大值")或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param      area: 滑动操作区域，可以为控件BY.text("画布")。目前仅在start或者end为坐标
                           时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域
                           的相对位置坐标。
        @param      pressure: 触控笔压力值, 范围[0, 1]
        @param      duration: 滑动时长, 单位秒, 默认0.3秒, 同时指定滑动时长和速度时, 仅速度生效
        @param      speed: 滑动速度, 同时指定滑动时长和速度时, 仅速度生效
        @example:    # 从类型为Slider的控件滑动到文本为最大的控件
                     driver.pen_slide(BY.type("Slider"), BY.text("最大"))
                     # 从坐标100, 200滑动到300，400
                     driver.pen_slide((100, 200), (300, 400))
                     # 从坐标100, 200滑动到300，400, 滑动时间为1秒
                     driver.pen_slide((100, 200), (300, 400), duration=1)
                     # 在类型为Slider的控件上从(0, 0)滑动到(100, 0)
                     driver.pen_slide((0, 0), (100, 0), area = BY.type("Slider))
        """
        self._driver_impl.pen_slide(start, end, area, pressure, duration, speed)

    @keyword
    def pen_drag(self, start: Union[ISelector, IUiComponent, tuple], end: Union[ISelector, IUiComponent, tuple],
                 area: Union[ISelector, IUiComponent, Rect] = None,
                 pressure: float = None, press_time: float = 1.5, duration: float = 1, speed: int = None):
        """
        @func       根据指定的起始和结束位置执行触控笔拖拽操作，起始和结束的位置可以为控件或者屏幕坐标
        @param      start: 拖拽起始位置，可以为控件BY.text("滑块")或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param      end: 拖拽结束位置，可以为控件BY.text("最大值")或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param      area: 拖拽操作区域，可以为控件BY.text("画布"), 或者使用find_component找到的控件对象。
                           目前仅在start或者end为坐标时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域
                           的相对位置坐标。
        @param      pressure: 触控笔压力值, 范围[0, 1]
        @param      press_time: 拖拽操作开始时，长按的时间, 默认为1.5秒
        @param      duration: 拖拽操作中滑动时长, 单位秒, 默认1秒, 同时指定滑动时长和速度时, 仅速度生效
        @param      speed: 拖拽过程中滑动速度, 同时指定滑动时长和速度时, 仅速度生效
        @example:    # 拖拽文本为"文件.txt"的控件到文本为"上传文件"的控件
                     driver.pen_drag(BY.text("文件.txt"), BY.text("上传文件"))
                     # 拖拽id为"start_bar"的控件到坐标(100, 200)的位置, 拖拽时间为2秒
                     driver.pen_drag(BY.key("start_bar"), (100, 200), duration=2)
                     # 在id为"Canvas"的控件上从相对位置(10, 20)拖拽到(100, 200)
                     driver.pen_drag((10, 20), (100, 200), area=BY.id("Canvas"))
                     # 在滑动条上从相对位置(10, 10)拖拽到(10, 200)
                     driver.pen_drag((10, 10), (10, 200), area=BY.type("Slider"))
        """
        self._driver_impl.pen_drag(start, end, area, pressure, press_time, duration, speed)

    @keyword
    def pen_inject_gesture(self, gesture: Gesture, pressure: float = None, speed: int = None):
        """
        @func 模拟触控笔自定义手势
        @param gesture: 触控笔自定义手势
        @param pressure: 触控笔压力值, 范围[0, 1]
        @param speed: 移动速度, 单位px/s, 当gesture中未指定操作时长是生效, 默认600px/s
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
        self._driver_impl.pen_inject_gesture(gesture, pressure, speed)

    @keyword
    def touchpad_swipe(self, direction: str, fingers=3, speed=None):
        """
        @func 模拟PC触控板滑动后手势
        @param direction: 滑动方向, 支持
                            UiParam.LEFT
                            UiParam.RIGHT
                            UiParam.UP
                            UiParam.DOWN
        @param fingers: 滑动手指数量, 仅支持3指和4指
        @param speed: 滑动速度
        @device_type: 2in1
        @example: # 触控板三指上滑后停顿
                  driver.touchpad_swipe_and_hold(UiParam.UP, fingers=3)
        """
        self._driver_impl.touchpad_swipe(direction, fingers, speed)

    @keyword
    def touchpad_swipe_and_hold(self, direction: str, fingers=3, speed=None):
        """
        @func 模拟PC触控板滑动后停顿手势
        @param direction: 滑动方向, 支持
                            UiParam.LEFT
                            UiParam.RIGHT
                            UiParam.UP
                            UiParam.DOWN
        @param fingers: 滑动手指数量, 仅支持3指和4指
        @param speed: 滑动速度
        @device_type: 2in1
        @example: # 触控板三指上滑后停顿
                  driver.touchpad_swipe_and_hold(UiParam.UP, fingers=3)
        """
        self._driver_impl.touchpad_swipe_and_hold(direction, fingers, speed)

    def click(self, target: Union[ISelector, IUiComponent, tuple], offset=None):
        """
        @func 模拟点击操作
        @param target: 点击操作目标
        @param offset: 点击坐标在目标控件区域的偏移值, 不设置时默认为(0.5, 0.5), 表示控件中心。支持设置范围是0到1
                       如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置
        @example: # 点击蓝牙控件
                  driver.click(BY.text("蓝牙"))
                  # 点击蓝牙控件左上角(偏移0, 0)
                  driver.click(BY.text("蓝牙"), offset=(0, 0))
                  # 点击蓝牙控件中偏移为0.8, 0.8的位置
                  driver.click(BY.text("蓝牙"), offset=(0.8, 0.8))
                  # 点击蓝牙控件正上方, 同蓝牙控件距离为蓝牙控件高度的80%的位置(0.5, -0.8)
                  driver.click(BY.text("蓝牙"), offset=(0.5, -0.8))
        """
        self._driver_impl.click(target, offset)

    def double_click(self, target: Union[ISelector, IUiComponent, tuple], offset=None):
        """
        @func 模拟点击操作
        @param target: 点击操作目标
        @param offset: 点击坐标在目标控件区域的偏移值, 不设置时默认为(0.5, 0.5), 表示控件中心。支持设置范围是0到1
                       如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置
        @example: # 点击蓝牙控件
                  driver.double_click(BY.text("测试按钮"))
                  # 点击蓝牙控件左上角(偏移0, 0)
                  driver.double_click(BY.text("测试按钮"), offset=(0, 0))
        """
        self._driver_impl.double_click(target, offset)

    def long_click(self, target: Union[ISelector, IUiComponent, tuple], press_time: float = 2, offset=None):
        """
        @func 执行长按操作, 可以指定长按时间
        @param target: 需要点击的目标，可以为控件查找条件, 控件对象或者屏幕坐标(通过tuple类型指定，
                       例如(100, 200)， 其中100为x轴坐标，200为y轴坐标), 或者使用find_component找到的控件对象
        @param press_time: 长按持续时间
        @param offset: 点击坐标在目标控件区域的偏移值, 不设置时默认为(0.5, 0.5), 表示控件中心。支持设置范围是0到1
                       如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置
        @example: # 长按文本为"按钮"的控件5秒
                  driver.long_click(BY.text("按钮"), press_time=5)
                  # 长按(100, 200)的位置5秒
                  driver.long_click((100, 200), press_time=5)
                  # 长按文本为"设置"的控件左上角(偏移0, 0)
                  driver.long_click(BY.text("设置"), offset=(0, 0))

        """
        self._driver_impl.long_click(target, press_time, offset)

    def input_text_on_current_cursor(self, text: str):
        """
        @func 在光标处输入文本, 该参数需要设备API level >= 20支持
        @param text: 输入的文本
        @example: # 在光标位置输入你好
                  driver.input_text_on_current_cursor("你好")
        """
        self._driver_impl.input_text_on_current_cursor(text)

    def rotate_crown(self, steps: int, speed: int = None):
        """
        @func 模拟表冠旋转
        @param steps: 旋转的步数, 正数表示顺时针旋转, 负数表示逆时针旋转
        @param speed: 旋转速度, 范围[1, 500], 默认为20
        @param # 表冠顺时针旋转50步
               driver.rotate_crown(50)
               # 表冠顺时针旋转50步
               driver.rotate_crown(-50)
               # 表冠顺时针旋转50步, 速度设置为60
               driver.rotate_crown(50, speed=60)
        """
        self._driver_impl.rotate_crown(steps, speed)

    def __str__(self):
        return f"UiDriver#{self.device_sn}"


class AwBase(ABC):

    @property
    @abstractmethod
    def driver(self):
        pass

    @property
    def _device(self):
        """适配失败截图能力"""
        return getattr(self.driver, "_device", None)

    @property
    def device_sn(self):
        return getattr(self.driver, "device_sn", None)
