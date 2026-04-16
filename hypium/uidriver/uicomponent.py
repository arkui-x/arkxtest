from .by import By
from .frontend_api import frontend_api, FrontEndClass, get_api_level, do_hypium_rpc, ApiConfig
from hypium.model.basic_data_type import *

try:
    from devicetest.record_actions.record_action import record_action
except Exception:
    def record_action(func):
        return func
from .interface.uitree import IUiComponent


class UiComponent(FrontEndClass, IUiComponent):
    """
    Ui控件对象, 提供操作控件和获取控件属性接口。
    注意该类的方法只能顺序传参, 不支持通过key=value的方式指定参数
    ```
    from hypium.uidriver.uicomponent import UiComponent
    ```
    """

    def __init__(self, backend_obj_ref):
        super().__init__(backend_obj_ref)
        self.index = None

    def recover(self, device=None) -> bool:
        """启用uicomponent恢复"""
        result = self._recover_component()
        if result is False or result is None or "Component#" not in result:
            self._device.log.error("Fail to recover component: %s" % result)
            return False
        self.activate(result, self._device)
        return True

    def _recover_component(self):
        if self._sourcing_call is None:
            return False
        device = self._device
        api_name = self._sourcing_call[0]
        caller = self._sourcing_call[1]
        args = self._sourcing_call[2]
        for item in args:
            if isinstance(item, FrontEndClass):
                item.deactivate()
        try:
            result = FrontEndClass.call_backend_api(api_name, caller, args, can_defer=False, raw_return=True)
        except Exception as e:
            device.log.error("Rcp failed: %s %s" % (e.__class__.__name__, str(e)))
            return False
        if type(result) == list:
            if self.index is not None and len(result) > self.index:
                comp = result[self.index]
                result.pop(self.index)
                # release unused component
                FrontEndClass._clear_remote_objects(device, result)
                return comp
            else:
                device.log.error("Fail to recover component in list")
                return False
        else:
            return result

    def resolve(self, device):
        if self._resolved:
            return True
        return self.recover()

    @record_action
    @frontend_api(since=8)
    def click(self) -> None:
        """
        @func 点击控件
        """
        pass

    @record_action
    @frontend_api(since=8)
    def doubleClick(self) -> None:
        """
        @func 双击控件
        """
        pass

    @record_action
    @frontend_api(since=8)
    def longClick(self) -> None:
        """
        @func 长按控件
        """
        pass

    @frontend_api(since=8)
    def getId(self) -> int:
        """
        @func 获取控件id
        @return: 在api8之前返回系统为控件分配的数字id，在api9以及之后返回用户为控件设置的id
        """
        pass

    @frontend_api(since=8)
    def getKey(self) -> str:
        """
        @func: 获取用户设置的控件id值，该接口在api9之上被删除，使用getId()替换
        @return: 用户设置的控件id值
        """
        pass

    @frontend_api(since=8)
    def getText(self) -> str:
        """
        @func 获取控件text属性内容
        """
        pass

    @frontend_api(since=8)
    def getType(self) -> str:
        """
        @func 获取控件type属性内容
        """
        pass

    @frontend_api(since=8)
    def isClickable(self) -> bool:
        """
        @func 获取控件clickable属性内容
        """
        pass

    @frontend_api(since=8)
    def isScrollable(self) -> bool:
        """
        @func 获取控件scrollable属性内容
        """
        pass

    @frontend_api(since=8)
    def isEnabled(self) -> bool:
        """
        @func 获取控件enabled属性内容
        """
        pass

    @frontend_api(since=8)
    def isFocused(self) -> bool:
        """
        @func 获取控件focused属性内容
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def isLongClickable(self):
        """
        @func 获取控件longClickable属性内容
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def isChecked(self):
        """
        @func 获取控件checked属性内容
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def isCheckable(self):
        """
        @func 获取控件checkable属性内容
        """
        pass

    @frontend_api(since=10, hmos_since=8)
    def isSelected(self):
        """
        @func 获取控件selected属性内容
        """
        pass

    def inputText(self, text: str, mode: InputTextMode = None) -> None:
        """
        @func 向控件中输入文本
        """
        if mode is None:
            do_hypium_rpc(ApiConfig(since=8), "UiComponent.inputText", self, text)
        else:
            do_hypium_rpc(ApiConfig(since=20), "Component.inputText", self, text, mode)

    @frontend_api(since=9)
    def clearText(self) -> None:
        """
        @func 清除控件中的文本
        """
        pass

    @record_action
    def scrollSearch(self, by: By, vertical: bool = None, offset: int = None) -> 'UiComponent':
        """
        @func 在当前控件中上下滚动搜索目标控件
        @param by: 目标控件选择器By
        @param offset: 滚动起始点和结束点离控件边界的距离, 单位像素(设备api level >= 18支持)
        @param vertical: 是否垂直滚动, 默认为垂直滚动(设备api level >= 18支持), 注意由于底层接口限制, 如果指定offset参数,
                         必须同时指定vertical参数，否则会执行异常
        @example: # 滑动查找控件, 默认垂直方向滚动查找
                  scroll_area_component = driver.find_component(BY.type("List"))
                  if scroll_area_component:
                      # 垂直方向滚动查找
                      target_component = scroll_area_component.scrollSearch(BY.text("系统"))
                      # 水平方向滚动查找(api >= 18支持)
                      target_component = scroll_area_component.scrollSearch(BY.text("系统"), vertical=False)
                      # 设置滑动启动点距离滑动区域边缘的距离(deadzone), 注意不要超过可滑动区域控件高度(上下滑动)/宽度(左右滑动)的50%
                      # 注意由于底层接口限制, 如果指定offset参数, 必须同时指定vertical参数
                      target_component = scroll_area_component.scrollSearch(BY.text("系统"), vertical=True, offset=30)
        """
        return do_hypium_rpc(ApiConfig(8), "UiComponent.scrollSearch", self, by, vertical, offset)

    @frontend_api(since=9, hmos_since=8)
    def scrollToTop(self, speed: int = 600) -> None:
        """
        @func 滚动到当前控件顶部, 注意某些控件可滚动区域和控件实际大小不同可能导致滚动失效
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def scrollToBottom(self, speed: int = 600) -> None:
        """
        @func 滚动到当前控件底部, 注意某些控件可滚动区域和控件实际大小不同可能导致滚动失效
        """
        pass

    @frontend_api(since=10, hmos_since=8)
    def getDescription(self) -> str:
        """
        @func 获取控件description属性内容
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def getBounds(self) -> Rect:
        """
        @func 获取控件边框位置
        @return 表示控件边框位置的Rect对象, 可访问该对象的left/right/top/bottom属性获取边框位置
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def getBoundsCenter(self) -> Point:
        """
        @func 获取控件中心店位置
        @return 表示控件中心点的Point对象, 可访问该对象的x/y属性获取坐标值, 可以调用to_tuple()方法转换为python的(x, y)形式
        """
        pass

    @frontend_api(since=9, hmos_since=8)
    def dragTo(self, target: 'UiComponent') -> None:
        """
        @func 将当前控件拖拽到另一个控件上
        @param target: 另外一个控件对象
        """
        pass

    @frontend_api(since=9)
    def pinchOut(self, scale: float) -> None:
        """
        @func 将控件按指定的比例进行捏合放大
        @param scale: 指定放大的比例, 例如1.5
        """
        pass

    @frontend_api(since=9)
    def pinchIn(self, scale: float) -> None:
        """
        @func 将控件按指定的比例进行捏合缩小
        @param scale: 指定缩小的比例, 例如0.5
        """
        pass

    @frontend_api(since=18)
    def getHint(self):
        """
        @func 读取控件hint属性
        """
        pass

    @frontend_api(since=12)
    def getAllProperties(self) -> JsonBase:
        """
        @func 获取所有属性
        """
        pass


# register type and tools
FrontEndClass.frontend_type_creators['UiComponent'] = lambda ref: UiComponent(ref)
FrontEndClass.frontend_type_creators['Component'] = lambda ref: UiComponent(ref)
# convert return value to specific type according to api name
FrontEndClass.return_handlers['getBoundsCenter'] = lambda json_obj: Point.from_dict(json_obj)
FrontEndClass.return_handlers['getBounds'] = lambda json_obj: Rect.from_dict(json_obj)
FrontEndClass.return_handlers['getDisplaySize'] = lambda json_obj: Point.from_dict(json_obj)
