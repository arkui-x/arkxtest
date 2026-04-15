class UiDriverPropertyInDevice:
    # hypium的driver配置在device对象里边注册的key
    CONFIG = "_hypium_config"
    POP_WINDOW_SERVICE = "_hypium_pop_service"


class ComponentFindMode:
    UITEST = "uitest"  # 优先使用uitest原生控件查找模式
    UITREE = "uitree"  # 优先使用抓取控件树后本地解析模式


class ClearTextMode:
    ONCE = "once"
    ONE_BY_ONE = "one_by_one"


class DriverConfig:
    """
    配置driver执行参数, 暂未配置项
    """

    class PopWindowHandlerConfig:
        ENABLE = "enable"
        DISABLE = "disable"

    def __init__(self):
        self.component_find_backend = "uitest"
        # 弹窗消除模块配置
        self.pop_window_dismiss = "disable"

        # 弹窗消除模块是否在控件断言中生效
        self.enable_pop_window_dismiss_in_check = True

        # 触发弹窗消除后再次查找控件的超时时间, 通常需要比首次查找控件时间短降低时间开销
        self.pop_window_retry_find_timeout = 2

        self.after_action_wait_time = 1

        self.wait_time_after_pop_window_dismiss = 1

        self.clear_text_mode = ClearTextMode.ONCE

        self.clear_text_before_input = True

        self._out_of_screen_coord_for_input_text = (10000, 10000)

        self.screenshot_retry_times = 3

    def update_from_dict(self, config_dict):
        for key in config_dict.keys():
            if key in self.__dict__.keys():
                setattr(self, key, config_dict[key])

    @classmethod
    def from_dict(cls, config_dict):
        config = DriverConfig()
        for key in config_dict.keys():
            if key in config.__dict__.keys():
                setattr(config, key, config_dict[key])
        return config
