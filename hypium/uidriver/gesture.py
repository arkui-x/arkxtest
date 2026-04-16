import math
from typing import List
from hypium.model.basic_data_type import *
from .pointer_matrix import PointerMatrix
from hypium.utils import utils
from hypium.exception import HypiumOperationFailError


class PointerMatrixWrapper:

    def __init__(self, fingers: int, step_num_per_finger: int) -> 'PointerMatrix':
        self.fingers = fingers
        self.step_num = step_num_per_finger
        self.points = [(0, 0) for i in range(fingers * step_num_per_finger)]

    def setPoint(self, finger: int, step: int, point: Point, interval: int = None):
        if interval is not None:
            point.X += 65536 * interval
        self.points[finger * self.step_num + step] = (point.X, point.Y)


def calculate_steps(distance, time, sampling_time):
    """根据距离和时间计算需要注入的事件点数量"""
    if time < sampling_time or distance < 1:
        return 1
    steps = time / sampling_time
    if steps > distance:
        return distance
    return int(steps)


def _convert_gesture_pos(driver, gesture):
    if gesture.area is None:
        area_size = driver.get_display_size()
    else:
        area_size = gesture.area
    for step in gesture.steps:
        step.pos = utils.scale_to_position(step.pos, area_size)


def _calculate_gesture_steps(gesture, speed):
    total_steps = 0
    steps = gesture.steps
    for i in range(len(steps)):
        item = steps[i]
        if item.type == "start":
            if item.interval is not None:
                total_steps += 2
            else:
                total_steps += 1
        elif item.type == "move":
            last_item = steps[i - 1]
            offset_x = item.pos[0] - last_item.pos[0]
            offset_y = item.pos[1] - last_item.pos[1]
            distance = int(math.sqrt(offset_x ** 2 + offset_y ** 2))
            if item.interval is not None:
                time_ms = item.interval
            else:
                time_ms = int(distance / speed * 1000)
            total_steps += calculate_steps(distance, time_ms, gesture.get_sampling_time())
        elif item.type == "pause":
            points = int(item.interval / gesture.get_sampling_time())
            total_steps += points + 1
        else:
            raise TypeError(f"Invalid operation: {item.type}")
    return total_steps


def generate_points(pointer_matrix, gesture, finger_index, total_points, speed):
    cur_point = 0
    steps = gesture.steps
    for i in range(len(steps)):
        item = steps[i]
        if item.type == "start":
            if item.interval is not None:
                pointer_matrix.setPoint(finger_index, cur_point, Point(*item.pos), item.interval)
                cur_point += 1
                if len(steps) == 1:
                    # is a click, skip move point
                    pos = item.pos[0], item.pos[1]
                else:
                    pos = item.pos[0] + 3, item.pos[1]
                pointer_matrix.setPoint(finger_index, cur_point, Point(*pos))
                cur_point += 1
            else:
                pointer_matrix.setPoint(finger_index, cur_point, Point(*item.pos))
                cur_point += 1
        elif item.type == "move":
            last_item = steps[i - 1]
            offset_x = item.pos[0] - last_item.pos[0]
            offset_y = item.pos[1] - last_item.pos[1]
            distance = int(math.sqrt(offset_x ** 2 + offset_y ** 2))
            if item.interval is not None:
                time_ms = item.interval
            else:
                time_ms = int(distance / speed * 1000)
            cur_steps = calculate_steps(distance, time_ms, gesture.get_sampling_time())

            step_x = int(offset_x / cur_steps)
            step_y = int(offset_y / cur_steps)
            if item.interval is not None:
                pointer_matrix.setPoint(finger_index, cur_point - 1, Point(*last_item.pos),
                                        gesture.get_sampling_time())
                x, y = last_item.pos[0], last_item.pos[1]
                for inner_step in range(cur_steps):
                    x += step_x
                    y += step_y
                    pointer_matrix.setPoint(finger_index, cur_point, Point(x, y),
                                            gesture.get_sampling_time())
                    cur_point += 1
            else:
                pointer_matrix.setPoint(finger_index, cur_point - 1, Point(*last_item.pos))
                x, y = last_item.pos[0], last_item.pos[1]
                for inner_step in range(cur_steps):
                    x += step_x
                    y += step_y
                    pointer_matrix.setPoint(finger_index, cur_point, Point(x, y))
                    cur_point += 1
        elif item.type == "pause":
            points = int(item.interval / gesture.get_sampling_time())
            for _ in range(points):
                pointer_matrix.setPoint(finger_index, cur_point,
                                        Point(*item.pos), int(item.interval / gesture.get_sampling_time()))
                cur_point += 1
            pos = item.pos[0] + 3, item.pos[1]
            pointer_matrix.setPoint(finger_index, cur_point, Point(*pos))
            cur_point += 1
        else:
            raise RuntimeError("Invalid operation")

    step: GestureStep = steps[-1]
    while cur_point < total_points:
        pointer_matrix.setPoint(finger_index, cur_point, Point(*step.pos))
        cur_point += 1


def gestures_to_pointer_matrix(driver, gestures, speed=2000):
    fingers = len(gestures)
    steps = []

    for gesture in gestures:
        _convert_gesture_pos(driver, gesture)

    for gesture in gestures:
        current_finger_steps = _calculate_gesture_steps(gesture, speed)
        steps.append(current_finger_steps)

    driver.log_info(f"total points: {steps}")
    max_steps = max(steps)
    pointer_matrix = driver.create_pointer_matrix(fingers, max_steps)
    for finger_index, gesture in enumerate(gestures):
        generate_points(pointer_matrix, gesture, finger_index, max_steps, speed)
    return pointer_matrix


class Gesture:
    SAMPLE_TIME_MIN = 10
    SAMPLE_TIME_NORMAL = 50
    SAMPLE_TIME_MAX = 100

    """该类用于生成一个手势"""
    def __init__(self, area: Rect = None, sampling_time=50):
        """
        @func 生成一个手势对象
        @param area: 手势操作时如果使用相对坐标, 则area表示相对坐标的区域范围。如果不指定，相对坐标则为整个屏幕的相对坐标
        @param sampling_time: 手势操作注入点的采样时间
        """
        self.steps: List[GestureStep] = []
        if sampling_time < Gesture.SAMPLE_TIME_MIN or sampling_time > Gesture.SAMPLE_TIME_MAX:
            sampling_time = Gesture.SAMPLE_TIME_NORMAL
        self._sampling_time = sampling_time
        self._pause_sampling_time = self._sampling_time * 2
        self.area = area

    def get_sampling_time(self):
        return self._sampling_time

    def to_pointer_matrix(self, driver, speed=2000) -> PointerMatrix:
        return gestures_to_pointer_matrix(driver, (self, ), speed)

    def start(self, pos: tuple, interval: float = None) -> 'Gesture':
        """
        @func 手势操作开始
        @param pos: 开始点位置, 例如(100, 200)
        @param interval: 开始位置长按时间
        @example: gesture = Gesture()
                  # 开始位置长按2秒
                  gesture.start(2)
        """
        if len(self.steps) > 0:
            raise HypiumOperationFailError("Can't start twice")
        step = GestureStep(pos, "start", interval)
        self.steps.append(step)
        return self

    def pause(self, interval: float = 1.5) -> 'Gesture':
        """
        @func 在当前位置中途停顿interval秒
        @param: interval: 中途停顿时间，单位秒
        """
        if len(self.steps) <= 0:
            raise HypiumOperationFailError("please call gesture.start first")
        pos = self.steps[-1].pos
        step = GestureStep(pos, "pause", interval)
        self.steps.append(step)
        return self

    def move_to(self, pos: tuple, interval: float = None) -> 'Gesture':
        """
        @func 移动到指定位置pos
        @param pos: 开始点位置, 例如(100, 200)
        @param interval: 移动持续时间，单位秒
        """
        if len(self.steps) <= 0:
            raise HypiumOperationFailError("please call gesture.start first")
        step = GestureStep(pos, "move", interval)
        self.steps.append(step)
        return self

