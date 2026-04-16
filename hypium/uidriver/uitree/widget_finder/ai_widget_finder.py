from typing import List
from hypium.utils.logger import basic_log
from hypium.model.basic_data_type import Rect
from hypium.uidriver.uitree.page import WidgetInfo
from hypium.uidriver.uitree.widget_finder import WidgetFinder
from hypium.uidriver.uitree import Page

import cv2
import numpy as np


def mark_coordinate_with_star(image_path, coordinate, output_path=None):
    """
    在图片上用红色五角星标识出指定坐标位置。

    :param image_path: 图片路径
    :param coordinate: 坐标 (x, y)
    :param output_path: 输出图片路径，如果为None则显示图片而不保存
    """
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("图片无法读取，请检查路径是否正确。")

    # 五角星的参数
    x, y = coordinate
    size = 30  # 五角星的大小
    outer_radius = size
    inner_radius = size / 2.5

    # 计算五角星的顶点
    points = []
    for i in range(10):
        angle = np.pi / 2 + 2 * np.pi * i / 10  # 从12点方向开始
        if i % 2 == 0:
            radius = outer_radius
        else:
            radius = inner_radius
        px = int(x + radius * np.cos(angle))
        py = int(y - radius * np.sin(angle))
        points.append((px, py))

    # 将顶点转换为NumPy数组
    points = np.array(points, dtype=np.int32)

    # 绘制五角星
    cv2.fillPoly(image, [points], color=(0, 0, 255))  # 红色填充
    cv2.polylines(image, [points], isClosed=True, color=(0, 0, 255), thickness=2)  # 红色边框

    # 显示或保存图片
    if output_path:
        cv2.imwrite(output_path, image)
    else:
        cv2.imshow("Marked Image", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def draw_points_on_image(input_image_path, output_image_path, point1, point2):
    """
    在图片上绘制两个点，并保存处理后的图片。

    参数:
    - input_image_path: 输入图片的路径
    - output_image_path: 输出图片的路径
    - point1: 第一个点的坐标 (x, y)
    - point2: 第二个点的坐标 (x, y)
    """
    # 读取图片
    image = cv2.imread(input_image_path)
    if image is None:
        raise ValueError("图片读取失败，请检查路径是否正确。")

    # 在图片上绘制点
    cv2.circle(image, point1, 20, (0, 0, 255), -1)  # 红色点
    cv2.circle(image, point2, 20, (0, 0, 255), -1)  # 蓝色点

    # 保存处理后的图片
    cv2.imwrite(output_image_path, image)

    # 返回输出图片路径
    return output_image_path


class AiWidgetFinder(WidgetFinder):
    """
    指定语义类型控件查找器
    """

    @property
    def category(self):
        """
        返回支持查找的控件类别
        """
        return "Ui-Tar model widget finder"

    def is_support(self, description: str) -> bool:
        return True

    def _draw_ai_action_target(self, page, target):
        try:
            screenshot = cv2.imread(page.screenshot_path)
            h, w, *_ = screenshot.shape
            draw_points_on_image(page.screenshot_path, page.screenshot_path, (target.left, target.top),
                                 (target.right, target.bottom))
        except Exception as e:
            basic_log.warning("Fail to draw ai action screenshot: %s" % repr(e))

    def find_one(self, page: Page, description: str) -> WidgetInfo:
        from hypium_turbo.pilot.gui_agent_proxy import GUIAgentProxy
        org_target = GUIAgentProxy.ai_find_control(description, page)
        if org_target is None:
            return None
        target = Rect(left=org_target.x, right=org_target.x, top=org_target.y, bottom=org_target.y)
        # 绘制操作位置坐标
        self._draw_ai_action_target(page, target)
        return WidgetInfo(bounds=target, description=description)

    def find_all(self, page: Page, description: str) -> List[WidgetInfo]:
        """
        返回所有匹配的控件
        """
        result = self.find_one(page, description)
        if result:
            return [result]
        else:
            return []
