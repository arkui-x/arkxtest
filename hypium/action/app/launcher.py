import time
from devicetest.core.test_case import keyword
from hypium.uidriver.uitree import normalize_match_pattern
from hypium.dfx.tracker import Tracker, TrackerEvent
from hypium.uidriver import By, BY, UiComponent
from hypium.action.device.uidriver import UiDriver
from hypium.exception import *
from hypium.model.basic_data_type import *
from hypium.utils.test_api import record_time

TIME_WAIT_FOR_COMPONENT_SHORT = 1
IS_TEXT_FLAG_NAME = "__inner_is_text"


def _find_app_icon(driver: UiDriver, app_name: str, match_pattern: Union[MatchPattern, str]):
    # 查找GridItem中指定text的子节点所在的GridItem
    match_pattern_str = normalize_match_pattern(match_pattern)
    xpath = FormatString(
        "//GridItem/descendant::Text[fuzzy_match($app_name, @text, $match_pattern)]/ancestor::GridItem",
        app_name=app_name, match_pattern=match_pattern_str)
    return driver.find_component(BY.xpath(xpath))


def _find_component(driver: UiDriver, selectors: (By,), wait_time=0.1) -> UiComponent:
    """查找满足任意条件一个条件的控件"""
    for selector in selectors:
        # text区域点击无法启动应用, 需要找前边的图标
        if _is_text_selector(selector):
            return _find_app_icon(driver, selector.match_value, selector.match_pattern)
        else:
            component = driver.wait_for_component(selector, wait_time)
            if component is not None:
                return component
    else:
        return None


def _is_text_selector(selector):
    if getattr(selector, IS_TEXT_FLAG_NAME, False):
        return True
    else:
        return False


def _find_component_by_swipe(driver: UiDriver, conditions: (By,), max_swipe_times: int) -> UiComponent:
    # 首先回桌面
    driver.go_home()
    # 进行一次查找
    component = _find_component(driver, conditions)
    # 没有找打则再次返回桌面
    if component is None:
        # 再次会桌面, 返回首页
        driver.go_home()
        driver.wait_for_idle()
    # 开始滑动查找
    while True:
        component = _find_component(driver, conditions)
        if component is not None:
            return component
        if max_swipe_times <= 0:
            break
        driver.swipe(UiParam.LEFT, distance=60, swipe_time=0.1)
        max_swipe_times -= 1
    if component is None:
        window_info = driver.execute_shell_command("hidumper -s WindowManagerService -a '-a' | head -n 20")
        driver.log_info(window_info)
    return component


class Launcher:
    """桌面相关操作，包括滑动找到app并打开，返回桌面首页等, 仅支持手机"""

    @staticmethod
    @record_time
    def find_app_component(driver: UiDriver, app_name: str, match_pattern: MatchPattern = MatchPattern.EQUALS,
                           max_swipe_times: int = 8) -> UiComponent:
        """
        根据app名称查找桌面图标位置
        """
        if type(app_name) is not str:
            raise HypiumParamError("app_name", type(app_name), str)
        by_text = BY.text(app_name, match_pattern)
        setattr(by_text, IS_TEXT_FLAG_NAME, True)
        by_tuple = (by_text,)
        # 查找当前页面
        component = _find_component(driver, by_tuple, 0)
        Tracker.event(TrackerEvent.APP_INFO.id, event_name=TrackerEvent.APP_INFO.name, extraData={
            "bundle_name": app_name
        })
        if component:
            return component
        component = _find_component_by_swipe(driver, by_tuple, max_swipe_times)
        return component

    @staticmethod
    def find_component(driver: UiDriver, selector: By, max_swipe_times: int = 8) -> UiComponent:
        """
        @func 在桌面上滑动查找指定控件
        @param selector: By对象指定的控件查找条件
        @param max_swipe_times: 查找app时，最大滑动桌面屏幕的次数
        @example: # 在桌面滑动查找key为card的控件
                  component = Launcher.find_component(driver, BY.key("card"))
        """
        if type(selector) == By:
            conditions = (selector,)
        else:
            conditions = selector
        return _find_component_by_swipe(driver, conditions, max_swipe_times)

    @classmethod
    @keyword
    def start_app(cls, driver: UiDriver, app_name: str, match_pattern: MatchPattern = MatchPattern.EQUALS,
                  max_swipe_times: int = 8):
        """
        @func 滑动桌面找到名为 app_name 的应用并点击打开
        @param app_name: 需要查找的app名称(用户看到的app名称，不是包名，用UiView工具看到的text或者description)
        @param max_swipe_times: 查找app时，最大滑动桌面屏幕的次数
        @example: # 桌面点击启动抖音
                  Launcher.start_app(driver, "抖音")
        """
        app_component = cls.find_app_component(driver, app_name, match_pattern, max_swipe_times)
        if app_component is None:
            raise HypiumOperationFailError("No such app in Launcher: %s" % (app_name))
        driver.touch(app_component)

    @classmethod
    @keyword
    def go_home(cls, driver: UiDriver):
        """
        @func 通过按home键回到桌面主页, 如果在其他页面，一般需要连续按2次主页键才能保证回到桌面主页
        @example: # 回到桌面首页
                  Launcher.go_home(driver)
        """
        for _ in range(2):
            driver.press_home()
            driver.wait_for_idle(0.2, 1)
        time.sleep(0.5)

    @classmethod
    def _clear_recent_task(cls, driver, clear_button_keys):
        """点击垃圾桶按钮清理最近任务"""
        clear_button = None
        for item in clear_button_keys:
            clear_button = driver.wait_for_component(BY.key(item), timeout=3)
            if clear_button:
                break
        if not clear_button:
            raise HypiumOperationFailError("No clear button found")
        driver.touch(clear_button)

    @classmethod
    @keyword
    def clear_recent_task(cls, driver: UiDriver, clear_button_id: str = None):
        """
        @func 进入多任务界面并清理后台应用
        @param clear_button_id: 可选, 多任务界面清理按钮的id, 不设置则使用默认的id
        @example: # 进入多任务界面清理后台
                  Launcher.clear_recent_task(driver)
        """
        # 获取垃圾桶的id
        clear_button_keys = ["RecentClearAllView_Image_deleteFull", "RecentDeleteView_Image_deleteFull"]
        if clear_button_id:
            clear_button_keys.insert(0, clear_button_id)
        # 进入多任务
        driver.swipe_to_recent_task()
        # 尝试点击垃圾桶清理最近任务
        try:
            cls._clear_recent_task(driver, clear_button_keys)
        except Exception as e:
            driver.log.warning(f"Fail to clear recent task: {repr(e)}, press back")
            # 如果清理失败, 则按返回键
            driver.press_back()
