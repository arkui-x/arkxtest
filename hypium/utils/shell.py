from typing import Union
import subprocess
import platform
import os, signal


def kill_process_tree(process: subprocess.Popen):
    if process.poll() is not None:
        return
    if platform.system() == "Windows":
        subprocess.run("TASKKILL /F /PID {pid} /T".format(pid=process.pid), check=True, stdout=subprocess.DEVNULL)
    else:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)


def run_command(cmd: Union[str, list], timeout: float = 300) -> str:
    """
    @func: 在PC端执行shell命令
    @param: cmd: 命令内容
    @param: timeout: 超时时间, 单位秒
    """
    result = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, start_new_session=True)
    try:
        result.wait(timeout)
        stdout, stderr = result.communicate(timeout=timeout)
        echo = stdout + stderr
    except subprocess.TimeoutExpired as e:
        kill_process_tree(result)
        raise
    return echo
