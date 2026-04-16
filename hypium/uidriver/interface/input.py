from abc import ABC, abstractmethod


class InputDeviceType:
    TOUCHSCREEN = "touchscreen"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    TOUCHPAD = "touchpad"
    TS_PEN = "ts_pen"
    VOLUME_BUTTON = "volume_button"
    POWER_BUTTON = "power_button"
    # 旋钮
    KNOB = "knob"


class KeyboardInput(ABC):

    @abstractmethod
    def click(self, key):
        pass

    @abstractmethod
    def long_click(self, key, duration):
        pass

    @abstractmethod
    def double_click(self, key, interval):
        pass

    @abstractmethod
    def click_combination_key(self, key_list, duration):
        pass

    @abstractmethod
    def press(self, key):
        pass

    @abstractmethod
    def release(self, key):
        pass


class MouseInput:

    @abstractmethod
    def click(self, key):
        pass

    @abstractmethod
    def long_click(self, key, duration):
        pass

    @abstractmethod
    def double_click(self, key, interval):
        pass

    @abstractmethod
    def move_to(self, pos, step_len=30):
        pass

    @abstractmethod
    def scroll(self, steps, duration):
        pass

    @abstractmethod
    def drag_to(self, pos, step_len=30):
        pass

    # advanced
    @abstractmethod
    def press(self, key):
        pass

    @abstractmethod
    def release(self, key):
        pass



class TouchScreenInput:

    @abstractmethod
    def click(self, pos):
        pass

    @abstractmethod
    def long_click(self, pos, duration):
        pass

    @abstractmethod
    def double_click(self, pos, interval):
        pass

    @abstractmethod
    def swipe(self, start_pos, end_pos, duration):
        pass

    @abstractmethod
    def drag(self, start_pos, end_pos, duration, press_time):
        pass

    @abstractmethod
    def swipe_and_hold(self, start_pos, end_pos, duration, hold_duration=1):
        pass

    @abstractmethod
    def swipe_by_two_finger(self, start_pos1, end_pos1, start_pos2, end_pos2, duration):
        pass

    @abstractmethod
    def press(self, key):
        pass

    @abstractmethod
    def release(self, key):
        pass


