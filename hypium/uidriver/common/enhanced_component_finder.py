import time
from typing import Union
from hypium.exception import HypiumComponentNotFoundError, HypiumParamUiTargetError
from hypium.model import constant
from hypium.model.driver_config import DriverConfig
from hypium.uidriver import ArkUiDriver
from hypium.uidriver.interface.uitree import ISelector, IUiComponent

try:
    from devicetest.record_actions.record_action import record_action
except Exception:
    from hypium.utils.implement_utils import generic_deco as record_action

from hypium.dfx import tracker


def _get_wait_time(driver: ArkUiDriver, **kwargs):
    if "wait_time" in kwargs.keys():
        wait_time = kwargs.get("wait_time")
    elif hasattr(driver, "implicit_wait_time") and driver.implicit_wait_time >= 0:
        wait_time = driver.implicit_wait_time
    else:
        wait_time = constant.DEFAULT_TIMEOUT
    return wait_time


def _find_component_with_pop_window_handler(driver, selector: ISelector, timeout=3):
    # 没有找到控件则尝试消除弹窗然后重试
    pop_window_dismiss = False
    left_retry_times = 4
    enable_pop_window_dismiss = selector.get_config("pop_window_dismiss", True)
    while True:
        result = driver.waitForComponent(selector, int(timeout * 1000))
        if left_retry_times <= 0:
            break
        else:
            left_retry_times -= 1
        # 未找到控件时, 如果启用了弹窗消除则调用弹窗消除服务
        if result is None and enable_pop_window_dismiss:
            # 一些兼容性实现, 后续需要重构, 此处full_driver为UiDriver, driver为ArkUiDriver
            full_driver = getattr(driver, constant.FULL_DRIVER_TMP_KEY, None)
            if not full_driver:
                driver.log_debug("No full driver, can't call pop window dismiss")
                break

            if full_driver.config.pop_window_dismiss != DriverConfig.PopWindowHandlerConfig.ENABLE:
                break

            # 如果没有检查并消除弹窗, 则表示非弹窗遮挡, 不再进行二次查找
            if not full_driver.PopWindowService.handle_pop_window(max_try_times=1):
                break
            else:
                # 等待弹窗消失
                time.sleep(0.8)
                driver.waitForIdle(2, 2)
                pop_window_dismiss = True
                # 消除弹窗后尝试查找时缩短控件查找时间
                timeout = full_driver.config.pop_window_retry_find_timeout
        else:
            break
    # 识别并消除了弹窗, 根据结果进行打点
    if pop_window_dismiss:
        if result:
            tracker.track_adaptive_event(event_id="907003003", result="success")
        else:
            tracker.track_adaptive_event(event_id="907003003", result="failed")
    return result


@record_action
def _convert_to_uicomponent(driver: ArkUiDriver, target: Union[ISelector, IUiComponent], **kwargs) -> IUiComponent:
    """
    将选择器转换为后端对象, 如果已经是UiComponent对象则直接返回
    """
    target_type = type(target)
    if isinstance(target, str):
        from hypium.uidriver.uitree import BySelector
        target = BySelector().target(target)
    if isinstance(target, ISelector):
        by = target
        wait_time = _get_wait_time(driver, **kwargs)
        target = _find_component_with_pop_window_handler(driver, target, wait_time)
        if target is None:
            driver.dump_layout_debug_info()
            raise HypiumComponentNotFoundError(by)
        return target
    elif isinstance(target, IUiComponent):
        return target
    else:
        raise HypiumParamUiTargetError(target_type, is_no_pos=True)


def convert_to_uicomponent(driver: ArkUiDriver, target: Union[ISelector, IUiComponent], **kwargs) -> IUiComponent:
    """
    将By选择器转换为后端对象, 如果已经是UiComponent对象则直接返回
    """
    return _convert_to_uicomponent(driver, target, **kwargs)


def find_component_with_pop_window_handler(driver, selector: ISelector, timeout=3):
    """
    支持自动弹窗消除功能的控件查找接口
    """
    return _find_component_with_pop_window_handler(driver, selector, timeout)