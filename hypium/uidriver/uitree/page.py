import json
from hypium.model.basic_data_type import Rect
from hypium.utils import utils


class WidgetInfo:
    """
    存储控件的数据对象
    """

    def __init__(self, bounds: Rect, **kwargs):
        self.bounds = bounds
        self.extra_attrs = kwargs

    def __getattr__(self, item):
        return self.extra_attrs.get(item)


class Page:
    """
    设备显示的一个界面, 存储界面相关的信息
    """

    def __init__(self, screenshot_path, layout_path, display_id=-1):
        # 界面对应的屏幕id
        self.display_id = display_id
        # 界面截图文件路径
        self.screenshot_path = screenshot_path
        # 界面布局文件路径
        self.layout_path = layout_path

        # 界面原始信息
        # 界面截图
        self.screenshot = utils.cv_imread(screenshot_path)
