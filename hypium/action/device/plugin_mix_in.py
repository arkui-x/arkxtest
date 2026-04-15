import weakref
from hypium.model.driver_config import UiDriverPropertyInDevice
from hypium.utils.cached_property import cached_property


class PluginMixIn:
    """@inner 向driver对象中添加扩展功能模块"""

    @cached_property
    def Assert(self):
        """断言模块"""
        from hypium.checker.assertion import Assert
        return Assert(weakref.proxy(self))

    @cached_property
    def UiTree(self):
        """控件树查找模块"""
        from hypium.uidriver.uitree import UiTree
        return UiTree(weakref.proxy(self))

    @property
    def PopWindowService(self):
        try:
            from hypium.advance.pop_up_window_handler import PopWindowService
            # 由于driver的生命周期无法覆盖整个测试任务, 将弹窗消除模块托管到device对象中
            result = getattr(self._device, UiDriverPropertyInDevice.POP_WINDOW_SERVICE, None)
            if isinstance(result, PopWindowService):
                result.driver = weakref.proxy(self)
                return result
            else:
                result = PopWindowService(weakref.proxy(self))
                setattr(self._device, UiDriverPropertyInDevice.POP_WINDOW_SERVICE, result)
                return result
        except Exception as e:
            self.log.error("Fail to init module " + repr(e))
            raise