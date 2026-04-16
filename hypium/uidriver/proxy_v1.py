import json
import time
from datetime import datetime


def retry_setup_proxy(device):
    """connect失败时进行重试操作 -- hap模式"""
    if device.proxy is None:
        device.log.warning("proxy init failed, try again")
        time.sleep(2)
    else:
        return

    if device.proxy is None:
        # 失败后打印端口信息
        device.log.warning("proxy init failed")
        netstat_info = device.execute_shell_command("netstat -anp | grep :8011")
        device.log.info(netstat_info)
        ps_info = device.execute_shell_command("ps -ef|grep com.ohos.devicetest")
        device.log.info(ps_info)
        raise RuntimeError("Hypium Device Agent failed to start")

def rpc(device, msg: dict):
    msg_str = json.dumps(msg, ensure_ascii=False, separators=(',', ':'))
    full_msg = {"module": "com.ohos.devicetest.hypiumApiHelper",
                "method": "callHypiumApi", "params": ["context", msg_str],
                "request_id": datetime.now().strftime("%Y%m%d%H%M%S%f")}
    full_msg_str = json.dumps(full_msg, ensure_ascii=False, separators=(',', ':'))
    retry_setup_proxy(device)
    reply_str = device.proxy.rpc_for_hypium(full_msg_str)
    return reply_str
