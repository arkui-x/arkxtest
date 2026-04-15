import json
import time
from datetime import datetime
from hypium.uidriver.common import device_type_helper
import hypium.uidriver.setup_device as device_helper


def is_proxy_v2_mode(device):
    if not device_type_helper.is_ohos_device(device):
        return False
    if device_helper.get_device_agent_mode(device) != "hap":
        return True
    else:
        return False


def retry_setup_bin_proxy(device):
    """connect失败时进行重试操作 -- bin模式"""
    if device.abc_proxy is None:
        device.log.warning("proxy init failed, try again")
        time.sleep(2)
    else:
        return

    if device.abc_proxy is None:
        device.log.warning("proxy init failed")
        # 失败后打印端口信息
        netstat_info = device.execute_shell_command("netstat -anp | grep :8012")
        device.log.info(netstat_info)
        ps_info = device.execute_shell_command("ps -ef|grep uitest")
        device.log.info(ps_info)
        raise RuntimeError("Hypium Device Agent(bin) failed to start")


def rpc(device, msg: dict):
    full_msg = {"module": "com.ohos.devicetest.hypiumApiHelper",
                "method": "callHypiumApi", "params": msg,
                "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")}
    full_msg_str = json.dumps(full_msg, ensure_ascii=False, separators=(',', ':'))
    # mode abc
    retry_setup_bin_proxy(device)
    reply_str = device.abc_proxy.rpc_for_hypium(full_msg_str)
    return reply_str
