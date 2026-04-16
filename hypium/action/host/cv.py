from devicetest.core.test_case import keyword
from hypium.utils.cv import CVBasic
from hypium.model import Rect


class CV:
    """
    图像处理相关操作, 例如图片查找,裁剪,压缩,相似度对比, 清晰度计算等
    """

    @classmethod
    def imread(cls, file_path: str):
        """
        @func 读取一个图片, 返回OpenCV格式的图片对象, 支持中文路径
        @return 图片对象(numpy数组)
        @example: img = CV.imread("/path/to/image.jpeg")
        """
        return CVBasic.imread(file_path)

    @classmethod
    def imwrite(cls, img, filepath: str, quality: int = 80):
        """
        @func 以jpeg格式保存一张图片, 支持中文路径
        @param img: 图片对象(numpy数组)
        @param filepath: 保存图片的路径
        @param quality: jpeg图像质量, 范围0~100, 数值越小图像质量越低，图片占用空间越小
        @example: img = CV.imwrite("/path/to/image.jpeg")
        """
        return CVBasic.imwrite(img, filepath, quality)

    @classmethod
    @keyword
    def compress_image(cls, img_path: str, ratio: float = 0.5, quality=80, out_img_path: str = None):
        """
        @func 压缩图像, 保存为jpeg格式
        @param img_path: 需要压缩的图片地址
        @param ratio: 分辨率压缩比例范围0~1, 数值越小输出分辨率越低, 图片占用空间越小
        @param quality: jpeg图像质量, 范围0~100, 数值越小图像质量越低，图片占用空间越小
        @param out_img_path: 输出图片路径, 当设置为None时使用img_path作为输出图片路径，即在原图片上修改
        @example:  # 压缩图片, 修改原图片
                   CV.compress_image("/path/to/image.jpeg")
                   # 压缩图片, 修改原图片
                   CV.compress_image("/path/to/image.jpeg", out_img_path="/path/to/save_image.jpeg")
        """
        return CVBasic.compress_image(img_path, ratio, quality, out_img_path)

    @classmethod
    @keyword
    def crop_image(cls, img_path: str, area: Rect, out_img_path: str = None):
        """
        @func 裁剪图片
        @param img_path: 需要裁剪的图片路径
        @param area: 裁剪后保留的区域, 使用Rect类型指定
        @param out_img_path: 输出图片路径, 如果为None表示在原图上修改
        @example: # 裁剪图片，保留指定区域，原图修改
                  CV.crop_image("/path/to/image.jpeg", Rect(left=10, right=100, top=10, bottom=100))
                  # 裁剪图片，保留指定区域，保存到新图片
                  CV.crop_image("/path/to/image.jpeg", Rect(left=10, right=100, top=10, bottom=100),
                                 out_img_path=/path/to/new.jpeg")
        """
        return CVBasic.crop_image(img_path, area, out_img_path)

    @classmethod
    @keyword
    def find_image(cls, target_image_path: str, background_image_path: str, mode: str = "sift", **kwargs) -> Rect:
        """
        @func 在backgound_image_path对应的图片中查找target_image_path对应的图片位置
        @param target_image_path: 需要查找图片路径(查找的目标)
        @param background_image_path: 背景图片路径(查找的范围)
        @param mode: 图片匹配模式, 支持template和sift, 图片分辨率/旋转变化对sift模式影响相对较小，但sift模式难以处理缺少较复杂图案
                     的纯色，无线条图片
        @param kwargs: 其他配置参数
               min_match_point: sift模式支持, 最少匹配特征点数, 值越大匹配越严格, 默认为16
               similarity: template模式支持，图片最小相似度
        @example  # 在"background.jpeg"中查找"target.jpeg"
                  image_bounds = CV.find_image("target.jpeg", "background.jpeg")
        """
        return CVBasic.find_image(target_image_path, background_image_path, mode, **kwargs)

    @classmethod
    @keyword
    def compare_image(cls, image_path_a: str, image_path_b: str, mode: str = "template", with_color: bool = False) -> float:
        """
        @func 比较两张图片的相似度
        @param image_path_a: 第一张图片
        @param image_path_b: 第二张图片
        @param mode: 比较算法, "template" 表示相关系数算法比较, "sift"表示特征点算法比较
        @return 图片相似度0~1,, 数字越大相似度越高
        @example: # 比较image1.jpeg和image2.jpeg的相似度
                  similarity = CV.compare_image("/path/to/image1.jpeg", "/path/to/image2.jpeg")
        """
        return CVBasic.compare_image(image_path_a, image_path_b, mode, with_color)

    @classmethod
    @keyword
    def calculate_clarity(cls, image_path: str) -> float:
        """
        @func 计算图像的清晰度(通过检测图像中物体轮廓清晰度实现, 无法用于纯色的图片)
        @param image_path: 需处理的图片路径
        @return 代表图像清晰度的数值, 值越大表示图像越清晰, 内容不同的图片使用该方法计算出的清晰度
                不具备绝对的可比性, 内容相同的图片计算出的清晰度具有可比性。
        @example: # 计算图片清晰度
                  clarity = CV.calculate_clarity("/path/to/image.jpeg")
        """
        return CVBasic.calculate_clarity(image_path)

    @classmethod
    @keyword
    def calculate_brightness(cls, image_path: str):
        """
        @func 计算图像的平均亮度
        @param image_path: 需处理的图片路径
        @example: # 计算图片亮度
                  brightness = CV.calculate_brightness("/path/to/image.jpeg")
        """
        return CVBasic.calculate_brightness(image_path)

    @classmethod
    @keyword
    def encode_qr_code(cls, content: str, save_path: str):
        """
        @func 生成二维码
        @param content: 需要保存的二维码中的字符串
        @param save_path: 生成的二维码图片保存路径
        @example: # 生成二维码
                  CV.encode_qr_code("test_msg", "/path/to/save_qr_image.jpeg")
        """
        return CVBasic.encode_qr_code(content, save_path)

    @classmethod
    @keyword
    def decode_qr_code(cls, image_path: str) -> str:
        """
        @func 解析二维码
        @param image_path: 二维码图片路径
        @return 二维码图片中的文本信息, 如果解析二维码失败则返回空字符串
        @example: # 解析二维码
                  msg = CV.decode_qr_code("/path/to/qr_image.jpeg")
        """
        return CVBasic.decode_qr_code(image_path)

    @classmethod
    def get_video_resolution(cls, file_path: str) -> (int, int):
        """
        @func 读取视频分辨率
        @file_path PC端视频文件路径
        @return 视频分辨率, (宽度, 高度)
        @example # 获取视频分辨率
                 resolution = CV.get_video_resolution("test.mp4")
        """
        return CVBasic.get_video_resolution(file_path)




