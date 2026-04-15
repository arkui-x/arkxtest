def get_api_level(device):
    echo = device.execute_shell_command("param get const.ohos.apiversion").strip()
    if not echo.isdigit():
        device.log.error("Fail to get device api level from param, try old way")
        api_level = -1
    else:
        api_level = int(echo)
    if api_level < 0:
        device.log.error("Fail to get device api level from param, set to max")
        api_level = 99
    return api_level


def get_os_info(device):
    echo = device.execute_shell_command("param get const.product.software.version")
    os_info = echo.split(' ')
    if len(os_info) >= 2:
        os_type, os_version = os_info[0], os_info[1]
    else:
        os_type, os_version = echo, "unknown"
    return os_type, os_version