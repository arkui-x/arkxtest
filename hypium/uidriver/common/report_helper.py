import os.path
import time
from hypium.utils import utils
from hypium.utils.no_exception import no_exception


def _get_device(device):
    if hasattr(device, "_device"):
        return device._device
    else:
        return device


def get_screenshot_dir(device):
    device = _get_device(device)
    report_path = device.get_device_report_path()
    if not report_path:
        screenshot_dir = utils.get_tmp_dir()
    else:
        screenshot_dir = os.path.join(report_path, "screenshot")
    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)
    return screenshot_dir


def get_new_screenshot_path(device):
    device = _get_device(device)
    screenshot_dir = get_screenshot_dir(device)
    timestamp = int(time.time() * 1000)
    device_id = utils.normalize_device_sn_to_filename(device.device_sn)
    screenshot_path = os.path.join(screenshot_dir, f"{device_id}-{timestamp}.jpeg")
    return screenshot_path


def add_image_to_report(device, image_path: str, message="", **kwargs):
    device = _get_device(device)
    screeshot_dir = get_screenshot_dir(device)
    org_image_path = image_path
    if image_path.startswith(screeshot_dir):
        relative_path = os.path.basename(org_image_path)
        image_path = os.path.join("..", "screenshot", relative_path)
    if not message:
        message = org_image_path
    full_msg = f"<a href=\"{org_image_path}\"> " \
               f"{message}" \
               f"<img style=\"display:block\" src=\"{image_path}\" width=233/> " \
               f"</a>"
    if kwargs.get("log_level") == "debug":
        device.log.debug(full_msg)
    else:
        device.log.info(full_msg)

@no_exception
def add_cv2_image_to_report(device, image_obj, message="", **kwargs):
    """
    将cv2格式的图片对象保存并打印到html文件中
    """
    screenshot_path = get_new_screenshot_path(device)
    utils.cv_imwrite(image_obj, screenshot_path)
    add_image_to_report(device, screenshot_path, message, **kwargs)


@no_exception
def log_screenshot(driver, message="", **kwargs):
    """
    @func 截取屏幕截图并打印到html报告中
    @param driver: 设备驱动对象
    @param message: 截图上显示的文本消息
    @return 返回截图路径
    """
    img_path = get_new_screenshot_path(driver._device)
    img_path = driver.capture_screen(img_path)
    add_image_to_report(driver._device, img_path, message, **kwargs)
    return img_path