from typing import Any
from hypium.model.basic_data_type import UiParam


class HypiumNotSupportError(Exception):
    """
    操作在当前系统版本/设置上不支持时抛出该异常
    """

    def __init__(self, os_info: Any = None, msg: str = ""):
        msg = "[%s] %s" % (str(os_info), msg)
        super().__init__(msg)


class HypiumNotImplementError(Exception):
    """
    已经规划实现，当前代码还未完成时抛出该异常
    """

    def __init__(self, os_info: Any = None, msg: str = ""):
        if os_info is not None:
            msg = "[%s]" % (str(os_info)) + msg
        super().__init__(msg)


class HypiumOperationFailError(Exception):
    """
    接口操作失败时抛出该异常
    """

    def __init__(self, msg: str = ""):
        super().__init__(msg)


class HypiumParamError(HypiumOperationFailError):
    """
    传入参数错误时抛出该异常
    """

    def __init__(self, param_name=None, param_type=None, expected_type=None, msg=None):
        if msg is None:
            msg = "invalid param {}, type {}, expected {}".format(param_name, param_type,
                                                                  expected_type)
        super().__init__(msg)


class HypiumBackendObjectDropped(Exception):
    """意外情况导致后端对象被销毁时抛出该异常"""
    def __init__(self, backend_objects, msg = None):
        self.backend_objects = backend_objects
        if msg is None:
            msg = "backend object %s is dropped" % (str(backend_objects))
        super(HypiumBackendObjectDropped, self).__init__(msg)


class HypiumParamDirectionError(HypiumOperationFailError):
    """操作方向参数异常"""
    def __init__(self, direction, supported=None):
        if supported is None:
            supported = "{}, {}, {}, {}".format(
                UiParam.RIGHT,
                UiParam.LEFT,
                UiParam.UP,
                UiParam.DOWN
            )
        msg = "invalid direction %s, expect [%s]" % (
            str(direction),
            supported
        )
        super().__init__(msg)


class HypiumParamSideError(HypiumOperationFailError):
    """位置参数异常"""
    def __init__(self, side, msg=None):
        if msg is None:
            msg = "invalid side %s, expect [%s, %s, %s, %s]" % (
                str(side),
                UiParam.TOP,
                UiParam.BOTTOM,
                UiParam.LEFT,
                UiParam.RIGHT
            )
        super().__init__(msg)


class HypiumParamUiTargetError(HypiumOperationFailError):
    """Ui操作目标参数异常"""
    def __init__(self, target_type, is_no_pos=False):
        if is_no_pos:
            supported = "{}, {}".format("By", 'UiComponent')
        else:
            supported = "{}, {}, {}".format("By", 'UiComponent', 'tuple')

        msg = "invalid Ui Operation target {}, expect [{}]".format(
            target_type.__name__,
            supported
        )
        super().__init__(msg)


class HypiumParamAreaError(HypiumOperationFailError):
    """屏幕区域类型参数异常"""
    def __init__(self, target_type):
        supported = "{}, {}, {}".format("By", 'UiComponent', 'tuple')
        msg = "invalid Ui Operation target {}, expect [{}]".format(
            target_type.__name__,
            supported
        )
        super().__init__(msg)


class HypiumParamTouchModeError(HypiumOperationFailError):
    """触摸操作方式参数异常"""
    def __init__(self, touch_mode):
        msg = "invalid touch {}, expect [{}, {}, {}]".format(
            touch_mode,
            UiParam.NORMAL,
            UiParam.LONG,
            UiParam.DOUBLE
        )
        super().__init__(msg)


class HypiumComponentNotFoundError(HypiumOperationFailError):
    """控件查找失败异常"""
    def __init__(self, by):
        msg = "Can't find component with [{}]".format(by)
        super().__init__(msg)

class UiComponentDisappearError(Exception):

    def __init__(self, msg, comp):
        super().__init__(msg)
        self.comp = comp


class UiDriverAAMSError(Exception):

    def __init__(self, msg):
        super(UiDriverAAMSError, self).__init__(msg)

class UiDriverCreateError(Exception):

    def __init__(self, msg):
        super(UiDriverCreateError, self).__init__(msg)
