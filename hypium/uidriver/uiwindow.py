from .frontend_api import FrontEndClass, frontend_api
from hypium.model.basic_data_type import Rect, ResizeDirection, WindowMode


class UiWindow(FrontEndClass):
    """
    窗口对象, 提供窗口相关属性获取和窗口操作接口，
    注意该类的方法只能顺序传参, 不支持通过key=value的方式指定参数
    ```
    from hypium.uidriver.uiwindow import UiWindow
    ```
    """
    @frontend_api(since=9)
    def getBundleName(self) -> str:
        """
        @func 获取窗口对应的应用包名
        """
        pass

    @frontend_api(since=9)
    def getBounds(self) -> Rect:
        """
        @func 获取窗口边框位置
        """
        pass

    @frontend_api(since=9)
    def getTitle(self) -> str:
        """
        @func 获取窗口title属性内容
        """
        pass

    @frontend_api(since=9)
    def getWindowMode(self) -> WindowMode:
        """
        @func 获取窗口模式
        @return 返回WindowMode枚举类型，表示窗口所处的不同模式
        """
        pass

    @frontend_api(since=9)
    def isFocused(self) -> bool:
        """
        @func 获取窗口focused属性内容(是否获得焦点)
        """
        pass

    @frontend_api(since=9)
    def isActived(self) -> bool:
        """
        @func 获取窗口active属性内容(是否处于活动状态)
        """
        pass

    @frontend_api(since=9)
    def focus(self) -> None:
        """
        @func 使当前窗口获得焦点
        """
        pass

    @frontend_api(since=9)
    def moveTo(self, x: int, y: int) -> None:
        """
        @func 将当前窗口移动到指定坐标
        @param x: 坐标x值
        @param y: 坐标y值
        """
        pass

    @frontend_api(since=9)
    def resize(self, width: int, height: int, direction: ResizeDirection) -> None:
        """
        @func 根据传入的宽、高和调整方向来调整窗口的大小。适用于支持调整大小的窗口。
        @param width: 调整后窗口的宽度
        @param height: 调整后窗口的高度
        @param direction: 窗口调整的方向
        """
        pass

    @frontend_api(since=9)
    def split(self) -> None:
        """
        @func 将窗口模式切换成分屏模式。适用于支持切换分屏模式的窗口
        """
        pass

    @frontend_api(since=9)
    def maximize(self) -> None:
        """
        @func 将窗口最大化。适用于支持窗口最大化操作的窗口
        """
        pass

    @frontend_api(since=9)
    def minimize(self) -> None:
        """
        @func 将窗口最小化。适用于支持窗口最小化操作的窗口
        """
        pass

    @frontend_api(since=9)
    def resume(self) -> None:
        """
        @func 将窗口恢复到之前的窗口模式
        """
        pass

    @frontend_api(since=9)
    def close(self) -> None:
        """
        @func 关闭窗口
        """
        pass


FrontEndClass.frontend_type_creators['UiWindow'] = lambda ref: UiWindow(ref)
FrontEndClass.return_handlers['getWindowMode'] = lambda value: WindowMode(value)
