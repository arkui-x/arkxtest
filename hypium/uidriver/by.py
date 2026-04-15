from enum import unique, Enum
from typing import Tuple, List
from .frontend_api import FrontEndClass, frontend_api, get_api_level, ApiConfig, do_hypium_rpc
from .frontend_api import api8_to_api9
from hypium.model.basic_data_type import MatchPattern
from .interface.uitree import ISelector


class By(FrontEndClass, ISelector):
    """
    控件选择器, 在点击/查找控件接口中指定控件, 例如BY.text("中文").key("xxxx")
    注意该类的方法只能顺序传参, 不支持通过key=value的方式指定参数
    """
    local_auto_inc_id = 0

    def __init__(self, backend_obj_ref):
        super().__init__(backend_obj_ref)
        # By is always created by another By with a function call on it, so
        # record the source object, function_name and function_args.
        self.matchers = []
        self._config = {}
        self.match_value = ""
        self.match_pattern = MatchPattern.EQUALS
        self._sourcing_call: Tuple[By, str, List] = None

    def _read_arg_list(self, arg_list):
        # 读取匹配器rpc参数到对象的变量中
        if len(arg_list) <= 0:
            return
        if len(arg_list) == 1:
            self.match_value = arg_list[0]
        else:
            self.match_value, self.match_pattern = arg_list[:2]

    def try_defer_call(self, api_name, arg_list) -> Tuple[bool, 'By']:
        # Return an unresolved By and record its sourcing call.
        new_by = By('By_unresolved#{}'.format(By.local_auto_inc_id))
        new_by._resolved = False
        By.local_auto_inc_id = By.local_auto_inc_id + 1
        new_by._sourcing_call = (self, api_name, arg_list)
        new_by._read_arg_list(arg_list) # 记录匹配器的值和匹配模式, 供外部访问
        for item in arg_list:
            if type(item) == str and item.startswith("By"):
                raise RuntimeError("Fail")
        return True, new_by

    def deactivate(self):
        """标记对象同远程对象连接断开"""
        self._resolved = False
        if "seed" not in self._backend_obj_ref:
            self._backend_obj_ref = "By#reset"
            self.matchers = []
        if self._sourcing_call is not None:
            self._sourcing_call[0].deactivate()
            for item in self._sourcing_call[2]:
                if isinstance(item, FrontEndClass):
                    item.deactivate()

    def reset(self):
        """重置resolve状态, 在agent重启时重新进行resolve"""
        return self.deactivate()

    def recover(self, device=None):
        """后端对象销毁后, 尝试恢复该对象"""
        self.reset()
        return True

    def resolve(self, device):
        if self._resolved:
            return
        assert self._sourcing_call is not None
        # Do api converting when resolving by object
        source_by = self._sourcing_call[0]
        src_api = self._sourcing_call[1]
        source_api_args = self._sourcing_call[2]
        assert isinstance(source_by, By)
        api_level = get_api_level(device)
        if api_level >= 9:
            src_api = api8_to_api9(src_api)
        else:
            if src_api == "By.id":
                src_api = "By.key"
        # Ensure all object on the sourcing chain be resolved firstly, BY(ref=By#seed) is
        # pre-defined as the sourcing root: by=BY.id(1).text('2')
        is_from_seed = False
        if source_by._backend_obj_ref.endswith("seed"):
            is_from_seed = True
            source_by._resolved = True
            source_by._device = device
            # The Source BY is created before the device object is available, so it may use wrong
            # api level, we will correct it here
            if api_level < 9:
                source_by._backend_obj_ref = "By#seed"
            else:
                source_by._backend_obj_ref = "On#seed"
        else:
            source_by.resolve(device)
        device.log.debug('Begin to resolved {}, sourcing={}'.format(self._backend_obj_ref, self._sourcing_call))
        resolved = FrontEndClass.call_backend_api(src_api, source_by, source_api_args, can_defer=False, raw_return=True)
        if is_from_seed:
            source_by._resolved = False
            source_by._device = None
        self.activate(resolved, device)

    def _generate_by_selector(self):
        from .uitree import BySelector
        by_selector = BySelector.from_by(self)
        return by_selector

    @staticmethod
    def _convert_match_pattern(mp):
        from .uitree import convert_match_pattern
        return convert_match_pattern(mp)

    def set_config(self, config_name, config_value):
        """
        @func 设置控件查找相关策略配置
        @param config_name: 配置项名称
        @param config_value: 配置项值
        """
        self._config[config_name] = config_value
        return self

    def update_config(self, config: dict):
        self._config.update(config)

    def get_config(self, config_name, default_value=""):
        return self._config.get(config_name, default_value)

    @frontend_api(since=8)
    def text(self, txt: str, mp: MatchPattern = MatchPattern.EQUALS) -> 'By':
        """
        @func 通过文本选择控件
        @param txt: 控件的text属性值
        @param mp: 匹配模式, MatchPattern枚举变量
        """
        # 如果mp是int或者(mp为MatchPattern格式并且不为REGEXP)使用uitest控件查找模式
        using_uitest_selector = isinstance(mp, int) or (isinstance(mp, MatchPattern) and mp != MatchPattern.REGEXP)
        if not using_uitest_selector:
            return self._generate_by_selector().text(txt, self._convert_match_pattern(mp))
        return do_hypium_rpc(ApiConfig(since=8), "By.text", self, txt, mp)

    def key(self, key: str, mp: MatchPattern = None) -> 'By':
        """
        @func 通过key选择控件
        @param key: 控件的key属性值
        """
        if mp is not None:
            return self._generate_by_selector().key(key, self._convert_match_pattern(mp))
        return do_hypium_rpc(ApiConfig(since=8), "By.key", self, key)

    def id(self, compId: str, mp: MatchPattern = None) -> 'By':
        """
        @func 通过id选择控件
        @param: 控件的id属性值
        """
        if mp is not None:
            return self._generate_by_selector().key(compId, self._convert_match_pattern(mp))
        return do_hypium_rpc(ApiConfig(since=8), "By.id", self, compId)

    def type(self, tp: str, mp: MatchPattern = None) -> 'By':
        """
        @func 通过控件类型选择控件
        @param tp: 控件的类型属性值
        @param mp: 匹配模式, 默认全等匹配, 支持MatchPattern枚举中的类型
        """
        if mp is not None:
            return self._generate_by_selector().type(tp, self._convert_match_pattern(mp))
        return do_hypium_rpc(ApiConfig(since=8), "By.type", self, tp)

    def hint(self, hint: str, mp: MatchPattern = None):
        """
        @func 通过hint属性选择控件
        @param hint: 控件的类型属性值
        @param mp: 匹配模式, 默认全等匹配, 支持MatchPattern枚举中的类型
        """
        return do_hypium_rpc(ApiConfig(since=8), "By.hint", self, hint, mp)

    @frontend_api(since=8)
    def checkable(self, b: bool = True) -> 'By':
        """
        @func 通过checkable属性选择控件
        @param b: 目标控件的checkable属性值
        """
        pass

    @frontend_api(since=8)
    def longClickable(self, b: bool = True) -> 'By':
        """
        @func 通过longClickable属性选择控件
        @param b: 目标控件的longClickable属性值
        """
        pass

    @frontend_api(since=8)
    def clickable(self, b: bool = True) -> 'By':
        """
        @func 指定clickable属性选择控件
        @param b: 目标控件的clickable属性值
        """
        pass

    @frontend_api(since=8)
    def scrollable(self, b: bool = True) -> 'By':
        """
        @func 指定scrollable属性选择控件
        @param b: 目标控件的scrollable属性值
        """
        pass

    @frontend_api(since=8)
    def enabled(self, b: bool = True) -> 'By':
        """
        @func 指定enabled属性选择控件
        @param b: 目标控件的enabled属性值
        """
        pass

    @frontend_api(since=8)
    def focused(self, b: bool = True) -> 'By':
        """
        @func 指定focused属性选择控件
        @param b: 目标控件的focused属性值
        """
        pass

    @frontend_api(since=8)
    def selected(self, b: bool = True) -> 'By':
        """
        @func 指定selected属性选择控件
        @param b: 目标控件的selected属性值
        """
        pass

    @frontend_api(since=8)
    def checked(self, b: bool = True) -> 'By':
        """
        @func 指定checked属性选择控件
        @param b: 目标控件的checked属性值
        """
        pass

    @frontend_api(since=8)
    def isBefore(self, by: 'By') -> 'By':
        """
        @func 指定控件位于另一个控件之前
        @param by: 通过By指定的另外一个控件
        """
        pass

    @frontend_api(since=8)
    def isAfter(self, by: 'By') -> 'By':
        """
        @func 指定控件位于另一个控件之后
        @param by: 通过By指定的另外一个控件
        """
        pass

    @frontend_api(since=8)
    def description(self, description: str, mp: MatchPattern = MatchPattern.EQUALS) -> 'By':
        """
        @func 指定description属性选择控件
        @param description: 描述内容
        @param mp: 匹配模式, MatchPattern枚举变量
        """
        pass

    @frontend_api(since=8)
    def inWindow(self, package_name: str) -> 'By':
        """
        @func 指定控件位于指定应用的窗口
        @param package_name: 应用包名
        """
        pass

    @frontend_api(since=8)
    def within(self, by: 'By'):
        """
        @func 指定目前控件位于另外一个控件中
        @param by: 通过By指定的另外一个控件
        """
        pass


    def xpath(self, xpath: str):
        """
        @func 通过xpath查找控件, (注意xpath不能和其他查找方式同时使用, 通过xpath查找的控件对象
              只支持读取控件属性以及click/longClick/doubleClick/inputText/clearText操作)
        @param xpath: 控件的xpath路径
        """
        if self._sourcing_call:
            raise ValueError("xpath can't used with other matcher")
        from hypium.uidriver.uitree import BySelector
        return BySelector().xpath(xpath).update_config(self._config)

    def abspath(self, abspath: str):
        """
        @func 通过uiviewer插件中生成的非标准绝对路径(控件index从0开始)查找控件(注意abspath不能和其他查找方式同时使用,
              通过xpath查找的控件对象只支持读取控件属性以及click/longClick/doubleClick/inputText/clearText操作)
        @param abspath: uiviewer插件中生成的非标准绝对路径
        """
        if self._sourcing_call:
            raise ValueError("abspath can't used with other matcher")
        from hypium.uidriver.uitree import BySelector
        return BySelector().abspath(abspath).update_config(self._config)

    def format_matcher_info(self) -> str:
        result_str_list = []
        cur_by = self
        while cur_by is not None and "seed" not in cur_by._backend_obj_ref:
            if cur_by._sourcing_call is not None:
                next_by, matcher_name, matcher_value = cur_by._sourcing_call
                matcher_name = matcher_name.split('.')[1]
                matcher_str = "%s(%s)" % (matcher_name, str(matcher_value).strip('[]'))
                if next_by == cur_by:
                    break
                result_str_list.append(matcher_str)
                cur_by = next_by
            else:
                cur_by = None
        return "BY." + '.'.join(result_str_list)

    def __str__(self):
        return self.format_matcher_info()



# register type and tools, defer_resolved
FrontEndClass.frontend_type_creators['By'] = lambda ref: By(ref)
FrontEndClass.frontend_type_creators['On'] = lambda ref: By(ref)

"""the static global _By builder"""
BY = By("By#seed")
