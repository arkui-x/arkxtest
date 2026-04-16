import json
import platform
import shutil
import stat
import subprocess
import sys
import time
import os
import re
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException
from xdevice import platform_logger
from hypium.exception import *
from hypium.utils import utils, platform_info

DEFAULT_STARTUP_TIMEOUT = 8
DEFAULT_PAGE_LOAD_TIMEOUT = 50
DEFAULT_SCRIPT_TIMEOUT = 50
IMPLICIT_WAIT_TIMEOUT = 20
# 配置chromedriver日志级别的环境变量名称
CHROME_DRIVER_LOG_LEVEL_ENV_NAME = "CHROME_DRIVER_LOG_LEVEL"
logger = platform_logger("WebDriver")


class WebDriverSetupTool:
    """
    webdriver初始化工具, 需要用户自行部署chromedriver二进制文件到hypium安装目录的res/web_debug_tools/chromedriver_{version}目录下

    """

    def __init__(self, hypium_driver):
        """
        # 首先需要到chromedriver网站下载对应的chromedriver, 放到hypium安装目录的res/web_debug_tools/chromedriver_{version}目录下
        # 例如114版本的chromedriver放到res/web_debug_tools/chromedriver_114目录
        # 创建web初始化工具
        web_tools =  WebDriverSetupTool(driver)
        # 连接应用的的webview
        web_tools.connect("com.huawei.hmos.browser")
        # 调用webdriver中方法(selenium的webdriver)
        web_tools.driver.get("https://baidu.com")
        # 关闭/释放driver
        web_tools.close()
        """

        if hasattr(hypium_driver, "_device"):
            self.device = hypium_driver._device
        else:
            self.device = hypium_driver
        self.bundle_name = None
        self.log = self.device.log
        self._driver = None
        self._chromedriver_port = 9515
        self._host_no_port = "http://localhost"
        self._domain_socket_name = "webview_devtools_remote_"
        self._domain_socket_name_prefix = "webview_devtools_remote_"
        self.test_package = "no package"
        self.devtool_port = 9222
        self.devtool_host = "127.0.0.1"
        self.remote_devtool_port = 9222
        self._chrome_log_path = ""
        self._chromedriver_exe_path = ""
        self._chromedriver_search_path = ""

    @property
    def host(self):
        """
        chromedriver访问地址
        """
        return "%s:%s" % (self._host_no_port, self._chromedriver_port)

    @property
    def driver(self) -> webdriver.Remote:
        """
        @func selenium webdriver
        @example:
            web_tools =  WebDriverSetupTool(driver)
            # 连接应用的的webview
            web_tools.connect("com.huawei.hmos.browser")
            # 调用webdriver中方法(selenium的webdriver)
            web_tools.driver.get("https://baidu.com")
        """
        if self._driver is None:
            raise HypiumOperationFailError("webview not connect, please call connect first")
        return self._driver

    @driver.setter
    def driver(self, value):
        self._driver = value

    def set_chromedriver_exe_path(self, chromedriver_exe_path):
        """
        @func 设置使用的chromedriver可执行文件路径
        """
        self._chromedriver_exe_path = chromedriver_exe_path

    def set_chromedriver_exe_search_path(self, chromedriver_exe_search_path):
        """
        @func 设置chromedriver存放路径, 可以存放多个版本和架构的chromedriver, 根据平台和设备webview版本自动匹配合适的chromedriver版本
        @param chromedriver_exe_search_path: chromedriver保存路径, 目录结构如下:
               chromedriver_exe_search_path
               |--chromedriver_114
                  |-- chromedriver.exe  windows版本
                  |-- chromedriver      linux版本
                  |-- chromedriver.mac  mac版本
               |--chromedriver_132
                  |-- chromedriver.exe windows版本
                  |-- chromedriver     linux版本
                  |-- chromedriver.mac  mac版本
        """
        self._chromedriver_search_path = chromedriver_exe_search_path

    def _is_using_domain_socket(self, timeout: int = DEFAULT_STARTUP_TIMEOUT):
        for i in range(timeout):
            result = self.device.execute_shell_command(f"cat /proc/net/unix | grep {self._domain_socket_name_prefix}")
            self.device.log.debug(result)
            if self._domain_socket_name_prefix in result:
                return True
            else:
                time.sleep(0.8)
        return False

    def _find_forward_item(self):
        fport_infos = self.device.connector_command("fport ls")
        for line in fport_infos.split('\n'):
            result = re.search(r'(tcp:\d+ [a-zA-Z\d_-]+:[a-zA-Z\d_-]+)', line)
            if result is None:
                continue
            result = result.groups()[0]
            if str(self.devtool_port) in result and result.startswith('tcp:'):
                return result
        return None

    def _remove_forward(self):
        forward_item = self._find_forward_item()
        if forward_item:
            self.device.connector_command("fport rm " + forward_item)
            self.log.info(f"remove {forward_item}")

    def _get_devtools_ports(self):
        result = []
        devtools_port_info = self.device.execute_shell_command(f"cat /proc/net/unix|grep devtools")
        for line in devtools_port_info.split('\n'):
            items = line.split()
            if len(items) < 1:
                continue
            result.append(items[-1].strip('@'))
        return result

    def _find_devtools_port(self, process_name, timeout: int = DEFAULT_STARTUP_TIMEOUT):
        for i in range(timeout):
            process_info = self.device.execute_shell_command(f"ps -ef | grep {process_name}")
            devtools_ports = self._get_devtools_ports()
            # 查询名称为process_name的进程, 根据进程号去devtools端口中找对应的端口
            for line in process_info.split('\n'):
                items = line.split()
                if len(items) < 8:
                    continue
                pid = items[1]
                actual_process_name = items[7]
                if process_name not in actual_process_name:
                    continue
                for port in devtools_ports:
                    if pid not in port:
                        continue
                    else:
                        self.device.log.debug(f"Found devtools port {port} for {process_name}")
                        return port
            time.sleep(0.8)
        return None

    @property
    def devtools_url_no_protocol(self):
        return f"{self.devtool_host}:{self.devtool_port}"

    @property
    def devtools_url(self):
        return "http://" + self.devtools_url_no_protocol

    def _check_tcp_devtool_port(self, port):
        result = self.device.execute_shell_command(f"netstat -tlnp | grep :{port}")
        if str(port) not in result:
            self.device.log.info(result)
            raise RuntimeError(
                f"webview_devtools_remote is not open and devtools port {port} is not open, "
                f"check if web debug is enable for {self.bundle_name} and restart {self.bundle_name}")

    def _get_webview_core_version(self, retry=3):
        import urllib.request
        for _ in range(retry):
            try:
                devtools_url = self.devtools_url + "/json/version"
                response = urllib.request.urlopen(devtools_url, timeout=5)
                response_text = response.read().decode(encoding="utf-8", errors="ignore")
                try:
                    version_info = json.loads(response_text)
                except Exception as e:
                    self.device.log.error(f"Invalid json response: {response_text}, {e}")
                    continue
                browser_info = version_info.get("Browser", "")
                result = re.search(r"/([\d]+)\.", browser_info)
                if result is None:
                    self.device.log.info(f"unknown webview version info: {response_text}")
                    continue
                self.device.log.info(f"webview kernel version: " + result.groups()[0])
                return int(result.groups()[0])
            except Exception as e:
                self.device.log.error(f"Fail to read webview version: {e}")
            self.device.log.info("retry get webview version")
        return 114

    def _get_chromedriver_version(self, retry=3):
        import urllib.request
        query_url = self.host + "/status"
        for _ in range(retry):
            try:
                response = urllib.request.urlopen(query_url, timeout=5)
                response_text = response.read().decode(encoding="utf-8", errors="ignore")
                result = re.search(r"\"version\":\"([\d]+)\.", response_text)
                if result is None:
                    self.device.log.info(f"unknown chromedriver version info: {response_text}")
                    continue
                return int(result.groups()[0])
            except Exception as e:
                self.device.log.error(f"Fail to read chromedriver version: {e}")
            self.device.log.info("retry get chromedriver version")
        return 114

    def connect(self, bundle_name, remote_devtools_port=None, connection_timeout=60, options=None) -> webdriver.Remote:
        """
        @func 连接到指定应用的webview界面
        @param bundle_name: 目标应用包名
        @param remote_devtools_port: 目标应用webview调试端口, 使用系统内置webview内核的应用无需设置,
                                     如果是自定义webview内核的需要设置。
        @param connection_timeout: 连接超时时间
        @param options: 其他传递给selenium webdriver的options
        @example
            # 首先需要到chromedriver网站下载对应的chromedriver, 放到hypium安装目录的res/web_debug_tools/chromedriver_{version}目录下
            # 例如114版本的chromedriver放到res/web_debug_tools/chromedriver_114目录
            # 创建web初始化工具
            web_tools =  WebDriverSetupTool(driver)
            # 连接应用的的webview
            web_tools.connect("com.huawei.hmos.browser")
            # 调用webdriver中方法(selenium的webdriver)
            web_tools.driver.get("https://baidu.com")
            # 关闭/释放driver
            web_tools.close()
        """

        self.init_webview(bundle_name, remote_devtools_port,
                          connection_timeout, options)
        return self.driver

    def init_webview(self, bundle_name, remote_devtools_port=None, connection_timeout=60, options=None):
        self.bundle_name = bundle_name
        self.close()
        try:
            os.environ["GLOBAL_DEFAULT_TIMEOUT"] = str(connection_timeout)
            logger.info(f"set GLOBAL_DEFAULT_TIMEOUT to {connection_timeout} s")
            RemoteConnection.set_timeout(connection_timeout)
        except Exception as e:
            self.device.log.info(f"Fail to set connection timeout {repr(e)}")
        logger.info(f"set webdriver socket timeout: {connection_timeout} s")
        self._init_webview_new(bundle_name, remote_devtools_port=remote_devtools_port, options=options)

    def _setup_devtools_port_forward(self, bundle_name, remote_devtools_port, local_port: int = None):
        if local_port is None:
            unused_port = utils.get_unused_local_port()
        else:
            unused_port = local_port
        if unused_port:
            self.log.info("un-used port for webview is {}".format(unused_port))
            self.devtool_port = unused_port
        if remote_devtools_port is not None:
            # 手动指定devtools端口
            self.remote_devtool_port = remote_devtools_port
            self._check_tcp_devtool_port(self.remote_devtool_port)
            if isinstance(remote_devtools_port, int):
                self.device.connector_command(f"fport tcp:{self.devtool_port} tcp:{self.remote_devtool_port}")
            else:
                self.device.connector_command(f"fport tcp:{self.devtool_port} {self.remote_devtool_port}")
        elif self._is_using_domain_socket():
            # 使用系统web内核, 通过包名搜索应用webview端口
            self._domain_socket_name = self._find_devtools_port(bundle_name)
            if self._domain_socket_name is None:
                process_info = self.device.execute_shell_command("ps -ef | grep %s" % bundle_name)
                self.device.log.debug(process_info)
                raise RuntimeError("Fail to get devtools port for %s" % bundle_name)
            self.device.connector_command(f"fport tcp:{self.devtool_port} localabstract:{self._domain_socket_name}")
        else:
            # 未设置远程端口,
            self._check_tcp_devtool_port(self.remote_devtool_port)
            self.device.connector_command(f"fport tcp:{self.devtool_port} tcp:{self.remote_devtool_port}")

    def _backup_chromedriver_log(self):
        if os.path.exists(self._chrome_log_path):
            backup_path = self._chrome_log_path + '-' + utils.get_readable_timestamp() + ".bak"
            self.log.info("backup chromedriver log to: " + backup_path)
            shutil.copy(self._chrome_log_path, backup_path)
        else:
            self.log.warning("no chromedriver log to backup")

    def get_selenium_webdriver(self):
        if self.driver is None:
            raise HypiumOperationFailError("webview not init")
        return self.driver

    def switch_to_visible_window(self, index=0):
        """
        切换到visible状态为True的window, 默认切换到第一个, 可以通过index指定
        """
        org_index = index
        if index >= 0:
            all_window_handles = self.driver.window_handles
        else:
            all_window_handles = reversed(self.driver.window_handles)
            index += 1
        index = abs(index)
        if index >= len(self.driver.window_handles):
            raise ValueError(
                "total window handle %s, index [%s] out of bounds" % (len(self.driver.window_handles), org_index))

        for item in all_window_handles:
            self.driver.switch_to.window(item)
            visible = self.driver.execute_script("return document.visibilityState")
            if visible == "visible":
                if index == 0:
                    return
                else:
                    index -= 1
        self.log.warning("No visible window of index [%s] found, not switch" % org_index)

    def _init_webview_new(self, bundle_name, remote_devtools_port=None, options=None):
        err_msg = ""
        try:
            self.log.info("start to init WebDriver")
            # 启动chromedriver.exe驱动
            self._setup_devtools_port_forward(bundle_name, remote_devtools_port)
            if not isinstance(options, ChromiumOptions):
                self.log.info("No valid options pass in, create default")
                options = webdriver.ChromeOptions()
            else:
                try:
                    options_info = options.to_capabilities()
                    self.log.info(f"using pass in options: {options_info}")
                except Exception as e:
                    self.log.info(f"unknown options type: {e}")
            options.add_experimental_option(name="debuggerAddress", value=self.devtools_url_no_protocol)
            version = self._get_webview_core_version()
            self.init_chromedriver(version)
            try:
                self.driver = webdriver.Remote(command_executor=self.host, options=options)
                self.log.info("WebDriver init successfully, driver is {}".format(self.driver))
            except Exception as error:
                err_msg = str(error).split('\n')[0]
                self.log.error("connect failed {},try again!, error: {}".format(self.host, err_msg))
                # 连接失败时关闭chromedriver并重试
                self._kill_chromedriver(self._get_chrome_process_name())
                self._backup_chromedriver_log()
                self.init_chromedriver(version)
                # 重新尝试连接
                self.driver = webdriver.Remote(command_executor=self.host, options=options)
            # 设置超时时间
            self.driver.set_page_load_timeout(DEFAULT_PAGE_LOAD_TIMEOUT)
            self.driver.set_script_timeout(DEFAULT_SCRIPT_TIMEOUT)
            self.driver.implicitly_wait(IMPLICIT_WAIT_TIMEOUT)
            self.log.info("total web window handles %s" % self.driver.window_handles)
            self.driver.switch_to.window(self.driver.current_window_handle)
            self.log.info("current web window title: %s" % self.driver.title)
            self.log.info("current web window url: %s" % self.driver.current_url)
            is_success = True
        except Exception as error:
            forward_status = self.device.connector_command("fport ls")
            self.log.info(forward_status)
            all_errors = str(error).split('\n')
            max_line = min(len(all_errors), 5)
            err_msg = "\n".join(all_errors[:max_line])
            is_success = False
        if not is_success:
            self._backup_chromedriver_log()
            raise RuntimeError("WebDriver failed to init: " + err_msg)
        return self.driver

    def __getattr__(self, item):
        return getattr(self.driver, item)

    def _find_window(self, key, value, match_pattern):
        result = None
        current_handle = self.driver.current_window_handle
        for item in self.driver.window_handles:
            self.driver.switch_to.window(item)
            url = self.driver.current_url
            title = self.driver.title
            if key == "url" and utils.compare_text(url, value, match_pattern):
                result = item
                break
            elif key == "title" and utils.compare_text(title, value, match_pattern):
                result = item
                break
        self.driver.switch_to.window(current_handle)
        return result

    def get_all_windows(self, with_url=False):
        if not with_url:
            return self.driver.window_handles
        else:
            result = []
            current_handle = self.driver.current_window_handle
            for item in self.driver.window_handles:
                self.driver.switch_to.window(item)
                visible = self.driver.execute_script("return document.visibilityState")
                url = self.driver.current_url
                title = self.driver.title
                result.append(
                    {
                        "handle": item,
                        "url": url,
                        "title": title,
                        "visible": visible
                    }
                )
                self.driver.get_screenshot_as_file(f'{item}.png')
            self.driver.switch_to.window(current_handle)
            return result

    def get_current_window(self):
        return {"handle": self.driver.current_window_handle,
                "url": self.driver.current_url,
                "title": self.driver.title}

    def _is_chromedriver_running(self):
        process_name = "chromedriver"
        if platform.system() == "Windows":
            pid = "{}.exe".format(process_name)
            proc_sub = subprocess.Popen(["C:\\Windows\\System32\\tasklist"],
                                        stdout=subprocess.PIPE,
                                        shell=False)
            proc = subprocess.Popen(["C:\\Windows\\System32\\findstr", "/B", "%s" % pid],
                                    stdin=proc_sub.stdout,
                                    stdout=subprocess.PIPE, shell=False)
            try:
                (result, _) = proc.communicate(timeout=10)
                result = result.decode(encoding="utf-8", errors="ignored")
            except Exception as e:
                self.device.log.warning(f"Fail to get process status: {str(e)}")
                result = ""
        else:
            try:
                result = subprocess.check_output(f"ps -A|grep {process_name}", shell=True, timeout=10)
                result = result.decode(encoding="utf-8", errors="ignored")
            except Exception as e:
                self.device.log.warning(f"Fail to get process status: {str(e)}")
                result = ""
        if process_name in result:
            return True
        else:
            return False

    def _decode_bytes(self, data: bytes):
        for coding in ["utf-8", "gbk"]:
            try:
                result = data.decode(encoding=coding)
                return result
            except Exception as e:
                self.device.log.debug(f"Not {coding}, try next")
        return data

    def _kill_process_by_name(self, process_name):
        result = None
        echo = ""
        if platform_info.is_windows():
            result = subprocess.run(f"taskkill /F /IM {process_name}", capture_output=True)
        elif platform_info.is_mac():
            try:
                echo = subprocess.check_output(f"pgrep {process_name}", encoding="utf-8")
                echo = echo.strip().split("\n")[0]
                result = subprocess.run(f"kill {echo})", capture_output=True, shell=True)
            except Exception as e:
                echo = repr(e)
        else:
            result = subprocess.run(f"kill $(pidof {process_name})", capture_output=True, shell=True)

        if not result:
            self.device.log.wanring(f"Fail to stop {process_name}, error: {echo}")
            return
        if result.stdout:
            echo = self._decode_bytes(result.stdout)
        if result.stderr:
            echo += self._decode_bytes(result.stderr)
        self.device.log.info(f"stop {process_name}: {echo}")

    def _kill_chromedriver(self, chromedriver_process_name, retry=3):
        """
        停止chromedriver
        """
        for _ in range(retry):
            self._kill_process_by_name(chromedriver_process_name)
            time.sleep(1)
            if not self._is_chromedriver_running():
                return
        self.device.log.error("Fail to kill chromedriver")

    def _start_chromedriver(self, chrome_tool_path, args: list = None):
        """
        启动chromedriver
        """
        if not platform_info.is_windows():
            os.chmod(chrome_tool_path, stat.S_IRWXU)
        if args:
            cmd_list = args.insert(0, chrome_tool_path)
        else:
            temp_log_path = os.path.join(utils.get_system_temp_dir(), "chromedriver.log")
            chrome_driver_log_level = os.getenv(CHROME_DRIVER_LOG_LEVEL_ENV_NAME, "INFO")
            cmd_list = [chrome_tool_path, f"--log-level={chrome_driver_log_level}", "--log-path=" + temp_log_path,
                        "--port=%s" % self._chromedriver_port]
            logger.info(f"chromedriver log path: {temp_log_path}, log level: {chrome_driver_log_level}")
            self._chrome_log_path = temp_log_path
        process = subprocess.Popen(cmd_list)
        logger.info(f"chromedriver started, pid: {process.pid}")

    def _get_chrome_process_name(self):
        if platform_info.is_windows():
            return "chromedriver.exe"
        elif platform_info.is_mac():
            return "chromedriver.mac"
        else:
            return "chromedriver"

    def init_chromedriver(self, version=114):
        chrome_tool_name = self._get_chrome_process_name()
        builtin_path = ""
        if self._chromedriver_exe_path:
            chrome_tool_path = self._chromedriver_exe_path
        elif self._chromedriver_search_path:
            chrome_tool_path = os.path.join(self._chromedriver_search_path, f"chromedriver_{version}", chrome_tool_name)
        else:
            builtin_path = os.path.join("web_debug_tools", f"chromedriver_{version}", chrome_tool_name)
            chrome_tool_path = utils.get_resource_file(builtin_path)
        self.log.debug("chromedriver path:{}".format(chrome_tool_path))
        if chrome_tool_path is None:
            raise HypiumOperationFailError("No chromedriver found, path: [%s]" % builtin_path)
        if not os.path.isfile(chrome_tool_path):
            raise FileExistsError("{} not exists!".format(chrome_tool_path))
        if self._is_chromedriver_running():
            self.log.info("{} is running.".format(chrome_tool_name))
            chromedriver_version = self._get_chromedriver_version()
            if chromedriver_version < version:
                self.log.info(f"kill chromedriver {chromedriver_version}, webview version is {version}")
                self._kill_chromedriver(chrome_tool_name)
                # 等待1秒后, 重新启动chromedriver
                time.sleep(1)
                self._start_chromedriver(chrome_tool_path)
        # 启动chromedriver
        else:
            self.log.info("{} not running.starting the ChromeDriver. ".format(
                chrome_tool_path))
            self._start_chromedriver(chrome_tool_path)

    def close(self):
        if self._driver:
            self._remove_forward()
            self._driver.quit()
            self._driver = None
