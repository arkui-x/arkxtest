from abc import ABC, abstractmethod
from typing import Union, List, Any
from hypium.model import KeyCode
from hypium.uidriver.interface.uitree import ISelector, IUiComponent, IUiWindow
from hypium.model import Rect, MouseButton, WindowFilter, DisplayRotation
from hypium.uidriver.interface.log import ILog


class GeneralDriverModule:

    def __init__(self, driver):
        self._driver_impl = driver._driver_impl


class IUiDriverPenOperation:
    """
    触控笔相关操作
    """

    @abstractmethod
    def pen_click(self, target, offset=None):
        """
        @func 触控笔点击
        @param target: 点击目标, 支持控件/坐标和选择器
        @param offset: 点击坐标相对目标的偏移值,
                       如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置
                       默认点击目标中心点
        """
        pass

    @abstractmethod
    def pen_double_click(self, target, offset=None):
        """
        @func 触控笔点击
        @param target: 点击目标, 支持控件/
        @param offset: 点击坐标相对目标的偏移值,
                       如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置
                       默认点击目标中心点
        """
        pass

    @abstractmethod
    def pen_long_click(self, target, offset=None, pressure=None):
        """
        @func 触控笔点击
        @param target: 点击目标, 支持控件/坐标和选择器
        @param offset: 点击坐标相对目标的偏移值,
                       如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置
                       默认点击目标中心点
        """
        pass

    @abstractmethod
    def pen_swipe(self, direction, distance, start_point=None, area=None, pressure=None, duration=None, speed=None):
        """
        @func 触控笔指定方向滑动
        @param direction: 滑动方向
        @param distance: 滑动距离
        @param start_point: 滑动起始点
        @param area: 滑动区域
        @param pressure: 压力值
        @param duration: 滑动总时间，同时设定时速度优先生效
        @param speed: 滑动速度, 同时设定时速度优先生效
        """
        pass

    @abstractmethod
    def pen_slide(self, start, end, area=None, pressure=None, duration=None, speed=None):
        """
        @func 触控笔精确滑动
        @param area: 滑动区域
        @param pressure: 压力值
        @param duration: 滑动总时间，同时设定时速度优先生效
        @param speed: 滑动速度, 同时设定时速度优先生效
        """
        pass

    @abstractmethod
    def pen_drag(self, start, end, area=None, pressure=None, press_time=None, duration=None, speed=None):
        """
        @func 触控笔拖拽
        @param press_time: 在起点长按的时间
        @param area: 滑动区域
        @param pressure: 压力值
        @param duration: 滑动时间，同时设定时速度优先生效
        @param speed: 滑动速度, 同时设定时速度优先生效
        """
        pass

    @abstractmethod
    def pen_inject_gesture(self, gesture, pressure=None, speed=None):
        """
        @func 触控笔自定义手势
        @param gesture: 自定义手势
        @param pressure: 压力值
        @param speed: 滑动速度
        """
        pass


class IUiDriverTouchPadOperation:
    """
    触控板相关操作
    """

    @abstractmethod
    def touchpad_swipe(self, direction, fingers=3, speed=None):
        """
        @func 触控板滑动
        """
        pass

    @abstractmethod
    def touchpad_swipe_and_hold(self, direction, fingers=3, speed=None):
        """
        @func 触控板滑动后停顿
        """
        pass


class IScreenBasic:

    @abstractmethod
    def wake_up_display(self):
        """
        @func 唤醒屏幕
        """
        pass

    @abstractmethod
    def close_display(self):
        """
        @func 屏幕熄屏
        """
        pass

    @abstractmethod
    def unlock(self):
        """
        @func 解锁设备
        """
        pass

    @abstractmethod
    def set_sleep_time(self, sleep_time: float):
        """
        @func 设置熄屏时间
        @param sleep_time: 熄屏时间, 单位秒
        """
        pass

    @abstractmethod
    def restore_sleep_time(self):
        """
        @func 恢复默认熄屏时间
        """
        pass

    @abstractmethod
    def get_display_rotation(self) -> DisplayRotation:
        """
        @func 获取屏幕选择方向
        """
        pass

    @abstractmethod
    def set_display_rotation(self, rotation: DisplayRotation):
        """
        @func 设置屏幕旋转方向
        """
        pass

    @abstractmethod
    def set_display_rotation_enabled(self, enabled: bool):
        """
        @func 设置自动旋转开关
        """
        pass


class IUiDriver(ABC, IScreenBasic, IUiDriverPenOperation, IUiDriverTouchPadOperation):

    @property
    @abstractmethod
    def device_sn(self):
        """
        @func 读取设备sn号
        """
        pass

    @property
    @abstractmethod
    def log(self) -> ILog:
        """
        @func 日志模块
        """
        pass

    @abstractmethod
    def get_device_type(self) -> str:
        """
        @func 读取设备类型
        """
        pass

    @abstractmethod
    def get_os_type(self) -> str:
        """
        @func 读取设备操作系统类型
        """
        pass

    @abstractmethod
    def set_implicit_wait_time(self, wait_time: float):
        pass

    @abstractmethod
    def get_implicit_wait_time(self) -> float:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def add_hook(self, hook_type, hook_id, callback):
        """
        注册操作事件钩子
        """
        pass

    @abstractmethod
    def remove_hook(self, hook_type, hook_id):
        """
        移除操作事件钩子
        """
        pass

    @abstractmethod
    def remove_all_hooks(self, hook_type):
        """
        移除指定类型的所有钩子
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def pull_file(self, device_path: str, local_path: str = None, timeout: int = 60):
        """
        @func:     从设备端的传输文件到pc端
        @param:    local_path: PC侧保存文件的路径
        @param:    device_path: 设备侧保存文件的路径
        @param:    timeout: 拉取文件超时时间, 默认60秒
        @example:  # 从设备中拉取文件"/data/local/tmp/test.log"保存到pc端的test.log
                   driver.pull_file("/data/local/tmp/test.log", "test.log")
        """
        pass

    @abstractmethod
    def push_file(self, local_path: str, device_path: str, timeout: int = 60):
        """
        @func:   从pc端传输文件到设备端
        @param:  local_path: PC侧文件的路径
        @param:  device_path: 设备侧文件的路径
        @param:  timeout: 推送文件超时时间
        """
        pass

    @abstractmethod
    def has_file(self, file_path: str) -> bool:
        """
        @func 查询设备中是否有存在路径为file_path的文件
        @param file_path: 需要检查的设备端文件路径
        @example # 查询设备端是否存在文件/data/local/tmp/test_file.txt
                 driver.has_file("/data/local/tmp/test_file.txt")
        """
        pass

    @abstractmethod
    def wait(self, wait_time: float):
        """
        @func: 等待wait_time秒
        @param: wait_time: 等待秒数
        """
        pass

    @abstractmethod
    def start_app(self, package_name: str, page_name: str, params: str = "", wait_time: float = 1):
        """
        @func           根据包名启动指定的app
        @param          package_name: 应用程序包名，bundle name
        @param          page_name: 应用内页面名称，ability name
        @param          params: 其他传递给aa的命令行参数
        @param          wait_time: 发送启动指令后，等待app启动的时间

        """
        pass

    @abstractmethod
    def stop_app(self, package_name: str, wait_time: float = 0.5):
        """
        @func      停止指定的应用
        @param     package_name: 应用程序包名
        @param     wait_time: 停止app后延时等待的时间, 单位为秒
        @example   # 停止com.ohos.settings
                   driver.stop_app("com.ohos.settings")

        """
        pass

    @abstractmethod
    def has_app(self, package_name: str) -> bool:
        """
        @func 查询是否安装指定包名的app
        @param package_name: 需要检查的应用程序包名
        """
        pass

    @abstractmethod
    def current_app(self) -> (str, str):
        """
        @func 获取当前前台运行的app信息
        @return app包名和页面名称, 例如('com.huawei.hmos.settings', 'com.huawei.hmos.settings.MainAbility'),
                如果读取失败则返回(None, None)
        @example: package_name, page_name = driver.current_app()
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def uninstall_app(self, package_name: str, **kwargs):
        """
        @func 卸载App
        @param package_name: 需要卸载的app包名
        @example driver.uninstall_app(driver, "com.ohos.devicetest")
        """
        pass

    @abstractmethod
    def clear_app_data(self, package_name: str):
        """
        @func 清除app的数据
        @param package_name: app包名，对应Openharmony中的bundle name
        @example # 清除包名为com.tencent.mm的应用的所有数据
                 driver.clear_app_data("com.tencent.mm")
        """
        pass

    @abstractmethod
    def drag(self, start: Union[ISelector, tuple, IUiComponent], end: Union[ISelector, tuple, IUiComponent],
             area: Union[ISelector, IUiComponent] = None, press_time: float = 1, drag_time: float = 1,
             speed: int = None):
        """
        @func:       根据指定的起始和结束位置执行拖拽操作，起始和结束的位置可以为控件或者屏幕坐标
        @param:      start: 拖拽起始位置，可以为控件BY.text(“滑块”)或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      end: 拖拽结束位置，可以为控件BY.text(“最大值”)或者坐标(100, 200), 或者使用find_component找到的控件对象
        @param:      area: 拖拽操作区域，可以为控件BY.text("画布"), 或者使用find_component找到的控件对象。
                           目前仅在start或者end为坐标时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域
                           的相对位置坐标。
        @param:      press_time: 拖拽操作开始时，长按的时间, 默认为1s(设置暂时无效)
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

    @abstractmethod
    def touch(self, target: Union[ISelector, IUiComponent, tuple], mode: str = "normal",
              scroll_target: Union[ISelector, IUiComponent] = None, wait_time: float = 0.1, offset: tuple = None):
        """
        @func:    根据选定的控件或者坐标位置执行点击操作
        @param:   target: 需要点击的目标，可以为控件(通过By类指定)或者屏幕坐标(通过tuple类型指定，
                         例如(100, 200)， 其中100为x轴坐标，200为y轴坐标), 或者使用find_component找到的控件对象
        @param:   mode: 点击模式，目前支持:
                       "normal" 点击
                       "long" 长按（长按后放开）
                       "double" 双击
        @param:   scroll_target: 指定可滚动的控件，在该控件中滚动搜索指定的目标控件target。仅在
                                target为`ISelector`对象时有效
        @param:   wait_time: 点击后等待响应的时间，默认0.1s
        @param:   long_touch_time: mode为长按时, 配置长按时间
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def press_key(self, key_code: Union[KeyCode, int], key_code2: Union[KeyCode, int] = None,
                  mode="normal"):
        """
        @func 按下指定按键(按组合键请使用press_combination_key)
        @param key_code: 需要按下的按键编码
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
        pass

    @abstractmethod
    def press_home(self):
        """
        @func 按下HOME键

        @example: # 按下home键
                  driver.press_home()
        """
        pass

    @abstractmethod
    def press_back(self):
        """
        @func 按下返回键
        @example: # 按下返回键
                  driver.press_back()

        """
        pass

    @abstractmethod
    def go_home(self):
        """
        @func 返回桌面(不关心返回桌面的方式，自动决定最稳定的返回桌面方式)
        @example: # 返回桌面
                  driver.go_home()
        """
        pass

    @abstractmethod
    def go_back(self):
        """
        @func 返回上一级(不关心返回桌面的方式，自动决定最稳定的返回方式)
        @example: # 返回桌面
                  driver.go_back()
        """
        pass

    @abstractmethod
    def get_component_bound(self, component: Union[ISelector, IUiComponent]) -> Rect:
        """
        @func 获取通过By类指定的控件的边界坐标
        @return: 返回控件边界坐标的Rect对象，如果没找到控件则返回None

        @example # 获取text为按钮的控件的边框位置
                 bounds = driver.get_component_bound(BY.text(“按钮”))
                 # 获取控件对象的边框位置
                 component = driver.find_component(BY.text("按钮"))
                 bounds = driver.get_component_bound(component)
        """
        pass

    @abstractmethod
    def slide(self, start: Union[ISelector, tuple], end: Union[ISelector, tuple],
              area: Union[ISelector, IUiComponent], slide_time: float):
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
        pass

    @abstractmethod
    def swipe(self, direction: str, distance: int = 60, area: Union[ISelector, IUiComponent] = None, side: str = None,
              start_point: tuple = None, swipe_time: float = 0.3, speed: int = None):
        pass

    @abstractmethod
    def find_component(self, target: ISelector, scroll_target: ISelector = None) -> IUiComponent:
        pass

    @abstractmethod
    def find_all_components(self, target: ISelector, index: int = None) -> Union[IUiComponent, List[IUiComponent]]:
        pass

    @abstractmethod
    def find_window(self, filter: WindowFilter) -> IUiWindow:
        pass

    @abstractmethod
    def get_display_size(self) -> (int, int):
        """
        @func 返回屏幕分辨率
        @return (宽度, 高度)
        @example: # 获取屏幕分辨率
                  width, height = driver.get_display_size()
        """
        pass

    @abstractmethod
    def get_window_size(self) -> (int, int):
        """
        @func 获取当前处于活动状态的窗口大小
        @support OHOS
        @return (宽度, 高度)
        @example: # 获取当前活动状态的窗口大小
                  width, height = driver.get_window_size()
        """
        pass

    @abstractmethod
    def get_current_window(self) -> IUiWindow:
        pass

    @abstractmethod
    def get_component_property(self, component: Union[ISelector, IUiComponent], property_name: str) -> Any:
        pass

    @abstractmethod
    def capture_screen(self, save_path: str, in_pc: bool = True,
                       area: Union[Rect, ISelector, IUiComponent] = None) -> str:
        pass

    @abstractmethod
    def take_screenshot(self, mode: str = "key"):
        pass

    @abstractmethod
    def input_text(self, component: Union[ISelector, IUiComponent], text: str, mode=None):
        pass

    @abstractmethod
    def input_text_on_current_cursor(self, text: str):
        pass

    @abstractmethod
    def clear_text(self, component: Union[ISelector, IUiComponent]):
        pass

    @abstractmethod
    def move_cursor(self, direction: str, times: int = 1):
        pass

    @abstractmethod
    def wait_for_idle(self, idle_time: float, timeout: float):
        pass

    @abstractmethod
    def wait_for_component(self, by: ISelector, timeout: float) -> IUiComponent:
        pass

    @abstractmethod
    def wait_for_component_disappear(self, by: ISelector, timeout: float):
        pass

    @abstractmethod
    def to_abs_pos(self, x: float, y: float) -> (int, int):
        """
        @func 根据屏幕分辨率将相对坐标转换为绝对坐标
        @param x 相对x坐标，范围0~1
        @param y 相对y坐标，范围0~1
        @example # 将相对坐标(0.1, 0.8)转为屏幕上的绝对坐标
                 abs_pos = driver.to_abs_pos(0.1, 0.8)
        @return: 相对坐标对应的绝对坐标
        """
        pass

    @abstractmethod
    def pinch_in(self, area: Union[ISelector, IUiComponent, Rect], scale: float = 0.4, direction: str = "diagonal",
                 **kwargs):
        pass

    @abstractmethod
    def pinch_out(self, area: Union[ISelector, IUiComponent, Rect], scale: float = 1.6, direction: str = "diagonal",
                  **kwargs):
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def inject_gesture(self, gesture, speed: int = 2000):
        """
        @func 执行自定义滑动手势操作
        @param gesture: 描述手势操作的Gesture对象
        @param speed: 默认操作速度, 当生成Gesture对象的某个步骤中没有传入操作时间的默认使用该速度进行操作
        @example:   # 创建一个gesture对象
                    gesture = Gesture()
                    # 获取控件计算器的位置
                    pos = = driver.findComponent(BY.text("计算器")).getBoundsCenter()
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def mouse_click(self, pos: Union[tuple, IUiComponent, ISelector],
                    button_id: MouseButton = MouseButton.MOUSE_BUTTON_LEFT,
                    key1: Union[KeyCode, int] = None, key2: Union[KeyCode, int] = None):
        """
        @func 鼠标点击, 支持键鼠组合操作
        @param pos: 点击的位置, 支持位置, UiComponent对象以及By, 例如(100, 200), BY.text("确认")
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def press_power(self):
        """
        @func 按下电源键
        @example: # 按下电源键
                  driver.press_power()
        """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def swipe_to_back(self, side, times: int = 1, height: float = 0.5):
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
        pass

    @abstractmethod
    def swipe_to_recent_task(self):
        """
        @func 屏幕底端上滑停顿, 打开多任务界面
        @precondition 设备开启触摸屏手势导航
        @example: # 上滑停顿进度多任务界面
                  driver.swipe_to_recent_task()

        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def check_window(self, window: WindowFilter, title: str = None, bundle_name: str = None):
        """
        @func:     检查指定的window的属性是否符合预期
        @param:    title: 预期的窗口标题, None表示不检查
        @param:    bundle_name: 预期窗口所属的app包名, None表示不检查
        @support:  OHOS
        @example   # 检查当前焦点窗口的包名为com.ohos.setting
                   driver.check_window(WindowFilter().focused(True), bundle_name="com.ohos.settings")
        """
        pass

    @abstractmethod
    def check_component_exist(self, component: ISelector, expect_exist: bool = True, wait_time: int = 0,
                              scroll_target: Union[ISelector, IUiComponent] = None, ):
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
        pass

    @abstractmethod
    def check_component(self, component: Union[ISelector, IUiComponent], expected_equal: bool = True, **kwargs):
        """
        @func 检查控件属性是否符合预期
        @param component: 需要检查的控件, 支持By或者UiComponent对象
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
        pass

    @abstractmethod
    def check_window_exist(self, window: WindowFilter, expect_exist: bool = True):
        """
        @func:     检查指定的window是否存在
        @param:    window: 待检查的UI控件，使用By对象指定
        @param:    expect_exist: 是否期望窗口存在, True表示期望窗口存在，False表示期望窗口不存在
        @support:  OHOS
        @example:  # 检查包名为com.ohos.settings的窗口存在
                   driver.check_window_exist(WindowFilter().bundle_name("com.ohos.settings"))
                   # 检查标题为畅连的窗口不存在
                   driver.check_window_exist(WindowFilter().title("畅联"), expect_exist=False)
                   # 检查包名为com.ohos.settings, 标题为设置的窗口存在
                   driver.check_window_exist(WindowFilter().title("设置").bundle_name("com.ohos.settings"))
        """
        pass

    @abstractmethod
    def find_image(self, image_path_pc: str, mode="sift", **kwargs) -> Rect:
        pass

    @abstractmethod
    def touch_image(self, image_path_pc: str, mode: str = "normal", similarity: float = 0.95,
                    wait_time: int = 0.1, **kwargs):
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def inject_multi_finger_gesture(self, gestures, speed: int = 2000):
        """
        @func 注入多指手势操作
        @param gestures: 表示单指手势操作的Gesture对象列表，每个Gesture对象描述一个手指的操作轨迹
                         注意如果各个手势持续时间不同，时间短的手势操作会保持在结束位置，等待所有手势完成后才会抬起对应手指。
        @param speed: gesture的步骤没设置时间时, 使用该速度计算时间, 单独 像素/秒
        @example: # 创建手指1的手势, 从(0.4, 0.4)的位置移动到(0.2, 0.2)的位置
                  gesture1 = gesture.Gesture().start((0.4, 0.4)).move_to((0.2, 0.2), interval=1)
                  # 创建手指2的手势, 从(0.6, 0.6)的位置移动到(0.8, 0.8)的位置
                  gesture2 = gesture.Gesture().start((0.6, 0.6)).move_to((0.8, 0.8), interval=1)
                  # 注入多指操作
                  driver.inject_multi_finger_gesture((gesture1, gesture2))

        """
        pass

    @abstractmethod
    def two_finger_swipe(self, start1: tuple, end1: tuple, start2: tuple, end2: tuple,
                         duration: float = 0.5, area: Rect = None):
        """
        @func 执行双指滑动操作
        @param start1: 手指1起始坐标
        @param end1: 手指1起始坐标
        @param start2: 手指2起始坐标
        @param end2: 手指2结束坐标
        @param duration: 滑动操作持续时间
        @param area: 滑动的区域, 当起始结束坐标为(0.1, 0.2)等相对比例坐标时生效
        """
        pass

    @abstractmethod
    def multi_finger_touch(self, points: List[tuple], duration: float = 0.1, area: Rect = None):
        """
        @func 执行多指点击操作
        @param points: 需要点击的坐标位置列表，每个坐标对应一个手指, 例如[(0.1, 0.2), (0.3, 0.4)], 最多支持4指点击
        @param duration: 按下/抬起的时间，可实现多指长按操作, 单位秒
        @param area: 点击的区域, 当起始结束坐标为(0.1, 0.2)等相对比例坐标时生效
        @example: # 执行多指点击操作, 同时点击屏幕(0.1， 0.2), (0.3, 0.4)的位置
                  driver.multi_finger_touch([(0.1， 0.2), (0.3, 0.4)])
                  # 执行多指点击操作, 设置点击按下时间为1秒
                  driver.multi_finger_touch([(0.1， 0.2), (0.3, 0.4)], duration=2)
        """
        pass

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

    @abstractmethod
    def click(self, target: Union[ISelector, IUiComponent, tuple], offset=None):
        pass

    @abstractmethod
    def double_click(self, target: Union[ISelector, IUiComponent, tuple], offset=None):
        pass

    @abstractmethod
    def long_click(self, target: Union[ISelector, IUiComponent, tuple], press_time: float = 2, offset=None):
        pass

    @abstractmethod
    def rotate_crown(self, steps: int, speed: int = None):
        pass
