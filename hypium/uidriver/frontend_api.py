import json
import sys
import time
import typing
from enum import Enum
from functools import wraps
from typing import Tuple, Any, TypeVar
from hypium.uidriver.setup_device import setup_device
from hypium.exception import *
from hypium.model.basic_data_type import JsonBase
from hypium.uidriver.common import device_type_helper
from hypium.uidriver.system_info import get_os_info, get_api_level, is_valid_device
from hypium.uidriver.remote_object_manager import RemoteObjectManager
import hypium.uidriver.setup_device as device_helper
from .logger import hypium_inner_log
from hypium.uidriver import component_exception_handler
from hypium.uidriver import proxy_v1
from hypium.uidriver import proxy_v2

using_api_level = 100

# using TypeVar to enable auto complete for decorated function
T = TypeVar('T')

def set_using_api_level(api_level):
    global using_api_level
    using_api_level = api_level


class ApiConfig:

    def __init__(self, since=8, hmos_since=None):
        self.since = since
        self.hmos_since = hmos_since


class FrontEndClass:
    # the registration of frontend types, key: type name, value: tools function with ref arg
    frontend_type_creators = dict()  # key: typeName value: tuple(tools, defer_resolve)
    return_handlers = dict()
    # 调用增加perf_tag标记
    perf_tag_enable = False
    perf_tag = None
    PERF_ACTION_TYPE = "PerfActionType_"
    # 该变量已弃用
    agent_mode = "hap"

    # constructor, bind a backend_object by its reference
    def __init__(self, backend_obj_ref, device=None, is_static=False):
        self._backend_obj_ref = backend_obj_ref
        if device is None:
            self._resolved = False
        else:
            self._resolved = True
        self._device = device
        self._sourcing_call = None
        # 该远程对象为静态对象, 无需释放, 设置后release方法不会触发对该对象的清理
        self._is_static = is_static

    @staticmethod
    def get_remote_object_manager(device) -> RemoteObjectManager:
        """从设备对象中获取对应的远程对象管理器"""
        return getattr(device, "hypium_remote_obj_manager")

    @staticmethod
    def set_remote_object_manager(device):
        """设置远程对象管理器到对应device对象"""
        setattr(device, "hypium_remote_obj_manager", RemoteObjectManager(device))

    def set_device(self, device):
        if device is not None:
            self._resolved = True
            self._device = device

    # do reconnected with remote peer
    def recover(self, device=None):
        """后端重启时尝试恢复该对象，同远程对象建立连接"""
        return False

    def resolve(self, device):
        """后端重启时尝试恢复该对象，同远程对象建立连接"""
        pass

    # make the object connected with remote peer
    def activate(self, backend_obj_ref, device):
        """标记当前对象同远程对象建立连接, 对象有效"""
        self._backend_obj_ref = backend_obj_ref
        self._resolved = True
        if not hasattr(device, "hypium_remote_obj_manager"):
            FrontEndClass.set_remote_object_manager(device)
        remote_obj_manager: RemoteObjectManager = FrontEndClass.get_remote_object_manager(device)
        remote_obj_manager.set_remote_state_change_listener(device)
        remote_obj_manager.add_object(self)
        self._device = device

    # mark the object disconnected with remote peer
    def deactivate(self):
        """标记当前对象同远程对象断开连接, 对象无效"""
        self._resolved = False

    @classmethod
    def set_perf_tag(cls, tag="perf"):
        if not cls.perf_tag_enable:
            return
        cls.perf_tag = tag

    @classmethod
    def get_perf_tag(cls):
        """set performance operation tag for next operation"""
        return cls.perf_tag

    @classmethod
    def clear_perf_tag(cls):
        """clear performance operation tag"""
        if not cls.perf_tag_enable:
            return
        cls.perf_tag = None

    # destructor, make the bound backend_object as obsoleted
    def __del__(self):
        try:
            # 忽略析构错误
            self.release()
        except Exception as e:
            pass

    def release(self):
        """mark this object as not being used any longer"""
        if not self._resolved or self._is_static:
            return
        remote_object_manager = FrontEndClass.get_remote_object_manager(self._device)
        remote_object_manager.remove_object(self._backend_obj_ref)
        if remote_object_manager.need_clean_remote_objects() or "Driver#" in self._backend_obj_ref:
            garbages = remote_object_manager.get_garbages()
            result = FrontEndClass._clear_remote_objects(self._device, garbages)
            if result:
                remote_object_manager.total_clear_backend_object += len(garbages)
            remote_object_manager.clear_garbage()
        self._resolved = False
        self._backend_obj_ref = ""

    @staticmethod
    def _clear_remote_objects(device, garbage) -> bool:
        if device is None:
            hypium_inner_log.warning("No device for garbage clean")
            return False
        if sys.meta_path is None:
            return True
        if device_helper.get_device_agent_mode(device) == "bin":
            call = {'api': 'BackendObjectsCleaner', 'this': None, 'args': list(garbage)}
        else:
            call = {'api': 'ObjectCleaner', 'this': None, 'args': list(garbage)}
        try:
            result = FrontEndClass._do_call(device, call)
            if "exception" not in result.keys():
                return True
            else:
                return False
        except Exception as e:
            device.log.error("Fail to clean backend object: %s %s" % (e.__class__.__name__, str(e)))
            return False

    def __str__(self):
        return self._backend_obj_ref

    def __repr__(self):
        return self._backend_obj_ref

    # Defer the call to backend if possible. Return True/False indicating deferred,
    # and the deferred return value. Default behave: no defer.
    def try_defer_call(self, api_name, arg_list) -> Tuple[bool, Any]:
        return False, None

    """
    generic api implementor, procedures:
    1. marshal invocation as message, including apiId/Caller/parameters;
       if caller/parameter if of frontend_type_name, convert to backend_obj_ref
    2. forward invocation message remote via rpc.
    3. wait and receive reply message from rpc.
    4. check invocation error, throw if any, whit readable code and message
    5. convert result value to object, either primitive value or backend_object;
       for backend_object, construct by frontend_type_name and bind the reference.
    """

    @staticmethod
    def call_backend_api(api_name: str, frontend_obj: 'FrontEndClass',
                         arg_list: list, can_defer=True, api_level=None, raw_return=False) -> typing.Any:
        # step0. try to defer the call
        if can_defer and frontend_obj is not None:
            deferred, ret = frontend_obj.try_defer_call(api_name, arg_list)
            if deferred:
                return ret
        # check if caller object is ok, if not, try to recover it
        if frontend_obj is not None and not frontend_obj._resolved:
            hypium_inner_log.warning("call object is not resolved, try to recover it")
            result = frontend_obj.resolve(frontend_obj._device)
            if result is False:
                raise RuntimeError("Fail to resolve remote object, check device state or uitest state")
        # step1. immediate(un-deferred) call must target to a device, which should be
        # hold by the caller if its non-static api, otherwise should be pass as arg0
        target_device = None
        if frontend_obj is not None:
            target_device = frontend_obj._device
        elif arg_list is not None and len(arg_list) > 0:
            target_device = arg_list[0]
            arg_list = arg_list[1:]  # pop the device argument
        assert is_valid_device(target_device)
        if api_level is None:
            api_level = get_api_level(target_device)
        # step2. extract neatName: Class.method(xxx) ==> Class.method
        api = api_name
        neat_name_len = api_name.find('(')
        if neat_name_len > 0:
            api = api_name[0:neat_name_len]
        # step3. check each argument, convert FrontEndClass instance to the backend_ref
        recoverable_args = []
        org_arg_list = arg_list
        arg_list = org_arg_list.copy()
        # 移除空元素
        arg_list = list(filter(lambda x: x is not None, arg_list))
        for index in range(0, len(arg_list)):
            arg = arg_list[index]
            if arg is None:
                raise ValueError('Argument cannot be null')
            elif isinstance(arg, Enum):  # convert enum value to integer
                arg_list[index] = arg.value
            elif isinstance(arg, FrontEndClass):
                # in immediate call, all args must be resolved
                arg.resolve(target_device)
                arg_list[index] = arg._backend_obj_ref
                recoverable_args.append(arg)
            elif isinstance(arg, JsonBase):
                # convert object to dict
                arg_list[index] = arg.to_dict(api_level)
            elif arg is None:
                # remove None(using None to indicate don't pass this param)
                arg_list.pop(index)
        # add perf_flag if it's been set
        if FrontEndClass.perf_tag:
            arg_list.append(FrontEndClass.PERF_ACTION_TYPE + FrontEndClass.perf_tag)
        # step4. inflate backend-api invocation data into json
        backend_obj_ref = None if frontend_obj is None else frontend_obj._backend_obj_ref
        call = {'api': api, 'this': backend_obj_ref, 'args': arg_list, 'message_type': "hypium"}
        # step5. call to remote and get reply message
        reply = FrontEndClass._do_call(target_device, call)
        if FrontEndClass.perf_tag:
            arg_list.pop()

        # step6. check and raise exception if any
        if 'exception' in reply.keys():
            error_msg = reply['exception']
            # 处理agent重启
            if "backend object" in error_msg:
                recoverable_args.append(frontend_obj)
                raise HypiumBackendObjectDropped(recoverable_args, error_msg)
            elif "WARNING" in error_msg:
                target_device.log.error(error_msg)
            elif isinstance(error_msg, dict) and "17000004" in str(error_msg.get("code")) or \
                    "dose not exist on current UI" in error_msg:
                raise UiComponentDisappearError(error_msg, frontend_obj)
            elif "Can not connect to AAMS" in str(error_msg):
                raise UiDriverAAMSError("Fail to connect AAMS")
            else:
                raise RuntimeError(error_msg)
        # step7. convert and return result (maybe primary data, jsonObject or backend-object)
        result = reply['result']
        if "Driver.create" in api_name and result == "dummy_ref":
            raise UiDriverAAMSError("driver create failed")
        # 如果不需要进行对象类型转换, 则直接返回(用于对象恢复时, 直接获取远程对象引用字符串)
        if raw_return:
            return result
        if type(result) is list:  # case1: convert and return value list
            frontend_values = []
            index = 0
            need_recover = False
            # add support for components recover after disconnection
            if "findComponents" in api_name:
                need_recover = True
            for value in result:
                item = FrontEndClass._convert_to_frontend_value(value, target_device)
                frontend_values.append(item)
                if need_recover:
                    item._sourcing_call = (api_name, frontend_obj, org_arg_list)
                    # record component index for recovering
                    item.index = index
                index += 1
            return frontend_values
        else:  # case 1: return single value
            item = FrontEndClass._convert_to_frontend_value(result, target_device, api)
            if "UiComponent" in type(item).__name__:
                item._sourcing_call = (api_name, frontend_obj, org_arg_list)
            return item

    # convert from backend object reference to frontend type object.
    @staticmethod
    def _convert_to_frontend_value(value, device, api_name=None):
        if value is None:  # return null
            return None

        # if there is a return value handle for this api, using it
        if api_name:
            method_name = api_name.split('.')[1]
            return_handler = FrontEndClass.return_handlers.get(method_name, None)
            if return_handler:
                return return_handler(value)

        # jsonObject, convert to python bean object
        if type(value) is dict:
            obj = JsonBase()
            for attr, value in value.items():
                setattr(obj, attr, value)
                # api9 部分数据字段名字发生变化，这里进行暂时适配
                setattr(obj, attr.upper(), value)
            return obj
        if not isinstance(value, str):  # none-string primitive value, return it
            return value
        creator_func = None
        for name, creator in FrontEndClass.frontend_type_creators.items():
            if value.find('{}#'.format(name)) == 0:
                creator_func = creator
                break
        if creator_func is None:  # plain string value
            return value
        # convert to frontend class object (wrapper), bind the target device
        frontend_obj: FrontEndClass = creator_func(value)  # like By("By#10")
        frontend_obj.activate(value, device)
        return frontend_obj

    # send call message to remote and wait for reply message
    @staticmethod
    def _do_call(device, msg_json) -> dict:
        if proxy_v2.is_proxy_v2_mode(device):
            reply_str = proxy_v2.rpc(device, msg_json)
        else:
            reply_str = proxy_v1.rpc(device, msg_json)
        try:
            if isinstance(reply_str, str):
                reply = json.loads(reply_str)
            else:
                device.log.error("rpc reply: {} is NOT a string, return empty".format(reply_str))
                return {"exception": reply_str}
        except Exception as e:
            raise RuntimeError("rpc reply: [%s] is NOT a valid json string, rpc call failed" % reply_str)
        return reply


# covert api8 class name to api 9 class name
def api8_to_api9(old_api_name: str):
    class_name, method_name = old_api_name.split('.')
    full_name_map = {
        "By.key": "On.id",
        "UiComponent.getKey": "Component.getId"
    }
    if old_api_name in full_name_map.keys():
        return full_name_map[old_api_name]

    class_name_map = {
        "UiDriver": "Driver",
        "UiComponent": "Component",
        "By": "On"
    }
    if class_name in class_name_map.keys():
        return "%s.%s" % (class_name_map[class_name], method_name)
    return old_api_name


def _get_device_from_args(*args):
    if args is None or len(args) <= 0:
        return None
    first_arg = args[0]
    if isinstance(first_arg, FrontEndClass):
        device = first_arg._device
        if device is None:
            return None
    else:
        device = first_arg
    setup_device(device)
    return device

def kill_device_process(device, process_name):
    """使用kill -9杀死设备端进程名称"""
    pid = device.execute_shell_command(f"pidof {process_name}")
    if isinstance(pid, str):
        pid = pid.strip()
        device.execute_shell_command(f"kill -9 {pid}")


def call_backend_api_with_retry(device, api_name, caller, params, max_try_times=3, **kwargs):
    """try to reconstruct backend object if it's gone"""
    for i in range(max_try_times):
        try:
            return FrontEndClass.call_backend_api(api_name, caller, list(params), **kwargs)
        except HypiumBackendObjectDropped as e1:
            if i >= max_try_times - 1:
                raise e1
            # try recover backend object
            device.log.info("Agent restart, try to recover object")
            if len(e1.backend_objects) <= 0:
                device.log.warning("No object to recover")
                raise e1
            for backend_object in e1.backend_objects:
                if backend_object is None:
                    continue
                if not backend_object.recover(device):
                    device.log.warning("Fail to recover object")
                    raise e1
        except UiComponentDisappearError as e2:
            device.log.warning(f"Component exception: [{e2}], try to recover")
            comp = e2.comp
            result, ret_value = component_exception_handler.handle_component_exception(comp, api_name.split(".")[-1])
            if result:
                return ret_value
            else:
                raise e2
        # 无障碍连接异常则重试
        except UiDriverAAMSError:
            device.log.warning(f"Fail to connect AAMS, try again[{i + 1}]")
            kill_device_process(device, "uitest")
    raise HypiumOperationFailError(f"Fail to call {api_name}")


def recover_component(device, by):
    device_api_level = min(get_api_level(device), using_api_level)
    # api名称转换适配
    if device_api_level >= 9:
        api_name = 'Driver.findComponent'
        caller = "Driver#0"
    else:
        api_name = 'UiDriver.findComponent'
        caller = "UiDriver#0"
    by.reset()
    by.resolve(device)
    call = {'api': api_name, 'this': caller, 'args': [by._backend_obj_ref], 'message_type': "hypium"}
    try:
        reply = FrontEndClass._do_call(device, call)
    except Exception as e:
        device.log.error("Rcp failed: %s %s" % (e.__class__.__name__, str(e)))
        return False
    if "exception" in reply.keys():
        device.log.error("Fail to recover component: %s" % (reply['exception']))
        return False
    if 'result' in reply.keys():
        return reply['result']
    else:
        return False


def _check_api_level(device, api_config: ApiConfig, raise_exception=True):
    """检查系统api是否满足需求"""
    global using_api_level
    device_api_level = min(get_api_level(device), using_api_level)
    if (not device_type_helper.is_ohos_device(device)) and api_config.hmos_since is not None:
        api_level_required = api_config.hmos_since
    else:
        api_level_required = api_config.since
    if api_level_required > device_api_level:
        os_info = get_os_info(device)
        if raise_exception:
            raise HypiumNotSupportError(os_info, "method not support, require_api_level %d > device_api_level %d" %
                                     (api_level_required, device_api_level))
        else:
            return -1
    return device_api_level


def do_hypium_rpc(api_config: ApiConfig, api_name, *args, **kwargs):
    """separate rpc call function, used to handle compatability requirements which frontend_api can't handle"""
    # api等级检查
    device = _get_device_from_args(*args)
    device_api_level = _check_api_level(device, api_config)
    # api名称转换适配
    api_name_real = api_name.replace("ArkUiDriver", "UiDriver")
    # api名称转换适配
    if device_api_level >= 9:
        api_name_real = api8_to_api9(api_name_real)

    # convert parameters
    caller = args[0] if len(args) > 0 and isinstance(args[0], FrontEndClass) else None
    # sing default converting routing
    arg0_index = 0
    argc = len(args)
    if caller is not None:
        arg0_index = 1
        argc = argc - 1
    params = [] if argc <= 0 else args[arg0_index:]
    return call_backend_api_with_retry(device, api_name_real, caller, params, api_level=device_api_level, **kwargs)


# the @frontend_api decorator, works as api version checker and function translator
def frontend_api(since: int, compatibility: bool = False, hmos_since: int = None):
    def decorate(func: T) -> T:
        api_name = func.__qualname__

        @wraps(func)
        def wrapper(*args, **kwargs):
            if len(kwargs) != 0:
                raise ValueError("%s not support key args" % api_name)
            api_config = ApiConfig(since, hmos_since)
            device = _get_device_from_args(*args)
            device_api_level = _check_api_level(device, api_config, raise_exception=False)
            if device_api_level > 0:
                # 执行正常rpc调用
                return do_hypium_rpc(api_config, api_name, *args)
            # 进行兼容性处理
            if compatibility:
                return func(*args, **kwargs)
            else:
                os_info = get_os_info(device)
                raise HypiumNotSupportError(os_info, "require_api_level %d > device_api_level %d"
                                         % (since, get_api_level(device)))

        return wrapper

    return decorate
