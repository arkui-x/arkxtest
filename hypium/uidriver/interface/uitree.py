from abc import ABCMeta, abstractmethod
from hypium.exception import HypiumNotSupportError
from hypium.model.basic_data_type import Rect, Point, JsonBase


class ISelector(metaclass=ABCMeta):

    @abstractmethod
    def update_config(self, config: dict) -> 'ISelector':
        """更新多个配置项"""
        pass

    @abstractmethod
    def set_config(self, config_name, config_value) -> 'ISelector':
        """配置额外的查找策略"""
        pass

    @abstractmethod
    def get_config(self, config_name, default_value=""):
        """读取查找策略配置"""
        pass


class IUiWindow(metaclass=ABCMeta):
    pass


class UiTree(metaclass=ABCMeta):

    @abstractmethod
    def find_all_components(self, selector, timeout):
        """
        @func 通过控件属性查找控件
        @param selector: 控件查找条件
        @return UiWidget控件对象数组, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找文本为"打开"的控件
                 items = driver.UiTree.find_all_component(BySelector().text("打开"))
                 # 点击控件
                 driver.touch(item.center)
        """
        pass

    @abstractmethod
    def find_component(self, selector, timeout):
        """
        @func 通过控件属性查找控件
        @param selector: 控件查找条件
        @return UiWidget控件对象, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找文本为"打开"的控件
                 item = driver.UiTree.find_component(BySelector().text("打开"))
                 # 点击控件
                 driver.touch(item.center)
        """
        pass

    @abstractmethod
    def find_component_by_path(self, path, timeout):
        """
        @func 通过hierarchy路径查找控件
        @param path: 控件路径, 使用Testing的UiView查看的path, 如/root[2]/Column/Flex/Text[2]
        @return UiWidget控件对象, 保存控件位置和属性, 可用于检查控件属性和点击操作
        @example # 查找根节点下第1个子节点的第2个子节点的第1个子节点的第3个字节点
                 item = driver.UiTree.find_component_by_path("/root[2]/Column/Flex/Text[2]")
                 # 点击控件
                 driver.touch(item.center)
        """
        pass

    @abstractmethod
    def find_component_by_relative_path(self, anchor, relative_path, timeout):
        """
        @func 通过相对路径查找控件
        @param anchor: 用于定位的锚点控件查找条件
        @param relative_path: 目标控件相对于锚点控件的路径, ..表示父节点, /1表示当前节点的第2个子节点(编号从0开始),
                              例如../../../3表示锚点控件的父节点的父节点的父节点的第4个子节点
        @return UiWidget控件对象, 保存控件位置和属性
        @example: # 根据相对路径查找text为toast的控件的父控件下的第二个子控件(../1)(索引从0开始)
                  # item = driver.UiTree.find_component_by_relative_path(BySelector().text("toast"), "../1")
                  # 打印控件的type属性
                  driver.log_info(item.type)
                  # 打印控件的id属性
                  driver.log_info(item.id)
                  # 打印控件的text属性
                  driver.log_info(item.text)
                  # 点击控件的中心点
                  driver.touch(item.center)
        """
        pass


class IUiComponent(metaclass=ABCMeta):

    @abstractmethod
    def getId(self) -> str:
        """
        @func 获取控件id
        @return: 在api8之前返回系统为控件分配的数字id，在api9以及之后返回用户为控件设置的id
        """
        pass

    @abstractmethod
    def getKey(self) -> str:
        """
        @func: 获取用户设置的控件id值，该接口在api9之上被删除，使用getId()替换
        @return: 用户设置的控件id值
        """
        pass

    @abstractmethod
    def getText(self) -> str:
        """
        @func 获取控件text属性内容
        """
        pass

    @abstractmethod
    def getType(self) -> str:
        """
        @func 获取控件type属性内容
        """
        pass

    @abstractmethod
    def isClickable(self) -> bool:
        """
        @func 获取控件clickable属性内容
        """
        pass

    @abstractmethod
    def isScrollable(self) -> bool:
        """
        @func 获取控件scrollable属性内容
        """
        pass

    @abstractmethod
    def isEnabled(self) -> bool:
        """
        @func 获取控件enabled属性内容
        """
        pass

    @abstractmethod
    def isFocused(self) -> bool:
        """
        @func 获取控件focused属性内容
        """
        pass

    @abstractmethod
    def isLongClickable(self):
        """
        @func 获取控件longClickable属性内容
        """
        pass

    @abstractmethod
    def isChecked(self):
        """
        @func 获取控件checked属性内容
        """
        pass

    @abstractmethod
    def isCheckable(self):
        """
        @func 获取控件checkable属性内容
        """
        pass

    @abstractmethod
    def isSelected(self):
        """
        @func 获取控件selected属性内容
        """
        pass

    @abstractmethod
    def getDescription(self) -> str:
        """
        @func 获取控件description属性内容
        """
        pass

    @abstractmethod
    def getBounds(self) -> Rect:
        """
        @func 获取控件边框位置
        @return 表示控件边框位置的Rect对象, 可访问该对象的left/right/top/bottom属性获取边框位置
        """
        pass

    @abstractmethod
    def getBoundsCenter(self) -> Point:
        pass

    @abstractmethod
    def click(self):
        pass

    @abstractmethod
    def doubleClick(self):
        pass

    @abstractmethod
    def longClick(self):
        pass

    @abstractmethod
    def clearText(self):
        pass

    @abstractmethod
    def inputText(self, text, mode=None):
        pass

    @abstractmethod
    def getAllProperties(self) -> JsonBase:
        pass

    def scrollSearch(self, selector: ISelector, *args, **kwargs):
        raise NotImplementedError()

    def getHint(self) -> str:
        return ""

    def exist(self) -> bool:
        """
        @func 判断控件是否存在, 提供默认实现
        """
        raise HypiumNotSupportError()
