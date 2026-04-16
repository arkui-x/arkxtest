# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.

try:
    import cv2
    import numpy as np
except ImportError:
    print("cv2 is not available")
from devicetest.core.test_case import keyword
from hypium.exception import *
from hypium.model.basic_data_type import Rect, Point
from devicetest.log.logger import platform_logger

hypium_inner_log = platform_logger("HypiumHostCV")


def _create_sift(edge_threshold=None, contrast_threshold=None, sigma=None):
    if hasattr(cv2, 'SIFT_create'):
        sift = cv2.SIFT_create(edgeThreshold=edge_threshold, contrastThreshold=contrast_threshold, sigma=sigma)
    else:
        sift = cv2.xfeatures2d.SIFT_create(edgeThreshold=edge_threshold)
    return sift


def compare_image_by_sift(im_source, im_search, min_match_point=16, edge_threshold=100, **kwargs):
    sift = _create_sift(edge_threshold, **kwargs)
    FLANN_INDEX_KDTREE = 0
    flann = cv2.FlannBasedMatcher({'algorithm': FLANN_INDEX_KDTREE, 'trees': 5}, dict(checks=50))
    kp_sch, des_sch = sift.detectAndCompute(im_search, None)
    if len(kp_sch) < min_match_point:
        return 0
    kp_src, des_src = sift.detectAndCompute(im_source, None)
    if len(kp_src) < min_match_point:
        return 0
    matches = flann.knnMatch(des_sch, des_src, k=2)
    good = []
    for m, n in matches:
        if m.distance < 0.5 * n.distance:
            good.append(m)
    hypium_inner_log.info("匹配到 %d 个相同特征点, 期望最小匹配点数为 %d" % (len(good), min_match_point))
    result = min(len(good) / len(des_sch), len(good) / len(des_src))
    return result


def find_image_by_sift(im_source, im_search, min_match_point=16, max_match=1,
                       edge_threshold=100, min_match_ratio=0.1, good_ratio=0.9, background_ratio=0.7,
                       area_check=True, **kwargs):
    sift = _create_sift(edge_threshold, **kwargs)
    FLANN_INDEX_KDTREE = 0
    flann = cv2.FlannBasedMatcher({'algorithm': FLANN_INDEX_KDTREE, 'trees': 5}, dict(checks=50))

    height, width, deep = im_source.shape
    width, height = (width * background_ratio, height * background_ratio)
    im_source = cv2.resize(im_source, (int(width), int(height)))

    kp_sch, des_sch = sift.detectAndCompute(im_search, None)
    if len(kp_sch) < min_match_point:
        return None

    kp_src, des_src = sift.detectAndCompute(im_source, None)
    if len(kp_src) < min_match_point:
        return None

    result = []
    while True:
        matches = flann.knnMatch(des_sch, des_src, k=2)
        good = []
        for m, n in matches:
            # 剔除掉跟第二匹配太接近的特征点
            if m.distance < good_ratio * n.distance:
                good.append(m)

        good_diff, diff_good_point = [], [[]]
        for m in good:
            diff_point = [int(kp_src[m.trainIdx].pt[0]), int(kp_src[m.trainIdx].pt[1])]
            if diff_point not in diff_good_point:
                good_diff.append(m)
                diff_good_point.append(diff_point)
        good = good_diff

        hypium_inner_log.info("匹配到 %d 个相同特征点, 期望最小匹配点数为 %d" % (len(good), min_match_point))
        hypium_inner_log.debug("match ratio %.2f" % (len(good) / len(kp_sch)))
        if len(good) < min_match_point:
            break

        sch_pts = np.float32([kp_sch[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        img_pts = np.float32([kp_src[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        # M是转化矩阵
        M, mask = cv2.findHomography(sch_pts, img_pts, cv2.RANSAC, 5.0)
        matches_mask = mask.ravel().tolist()

        # 计算四个角矩阵变换后的坐标，也就是在大图中的坐标
        h, w = im_search.shape[:2]
        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        try:
            dst = cv2.perspectiveTransform(pts, M)
            pypts = []
            for npt in dst.astype(int).tolist():
                pypts.append(tuple(npt[0]))

            lt, br = pypts[0], pypts[2]
            middle_point = (lt[0] + br[0]) / 2, (lt[1] + br[1]) / 2
            # check if the result is valid
            rect = Rect(pypts[0][0], pypts[2][0], pypts[0][1], pypts[2][1])
            img_sch_height, img_sch_width, img_sch_deep = im_search.shape
            img_search_size = img_sch_height * img_sch_width
            matched_img_width, matched_img_height = rect.get_size()
            matched_img_size = matched_img_width * matched_img_height
            hypium_inner_log.debug("match rect is %s" % str(rect))
            if area_check and (matched_img_size < img_search_size / 10 or matched_img_size > img_search_size * 10):
                hypium_inner_log.warning("invalid matched img size: %s, original img size %s" %
                                         (matched_img_size, img_search_size))
                return None

            if len(good) / len(kp_sch) < min_match_ratio:
                hypium_inner_log.warning("matched %s keypoints, target has %s keypoints, "
                                      "match ratio %.2f < %s" % (len(good), len(kp_sch),
                                                                 len(good) / len(kp_sch),
                                                                 min_match_ratio))
                return None

            middle_point = (middle_point[0] / background_ratio, middle_point[1] / background_ratio)
            rect.left, rect.right, rect.top, rect.bottom = rect.left / background_ratio, rect.right / background_ratio, \
                                                           rect.top / background_ratio, rect.bottom / background_ratio

            result.append(dict(
                result=middle_point,
                rectangle=rect,
                confidence=(matches_mask.count(1), len(good))  # min(1.0 * matches_mask.count(1) / 10, 1.0)
            ))
        except Exception as e:
            hypium_inner_log.warning("Fail to transform position to original image: %s" % str(e))
            return None
        if max_match and len(result) >= max_match:
            break
        # 从特征点中删掉那些已经匹配过的, 用于寻找多个目标
        qindexes, tindexes = [], []
        for m in good:
            qindexes.append(m.queryIdx)  # need to remove from kp_sch
            tindexes.append(m.trainIdx)  # need to remove from kp_img

        def filter_index(indexes, arr):
            r = []
            for i, item in enumerate(arr):
                if i not in indexes:
                    r.append(item)
            r = np.array(r)
            return r
        kp_src = filter_index(tindexes, kp_src)
        des_src = filter_index(tindexes, des_src)
    if len(result) <= 0:
        return None
    return result


class CVBasic:
    """图像处理相关操作, 例如图片查找,裁剪,压缩,相似度对比, 清晰度计算等"""

    @classmethod
    def imread(cls, file_path: str):
        """
        @func 读取一个图片, 返回OpenCV格式的图片对象, 支持中文路径
        @return 图片对象(numpy数组)
        """
        cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), -1)
        return cv_img

    @classmethod
    def imwrite(cls, img, filepath: str, quality: int = 80):
        """
        @func 以jpeg格式保存一张图片, 支持中文路径
        @param img: 图片对象(numpy数组)
        @param filepath: 保存图片的路径
        @param quality: jpeg图像质量, 范围0~100, 数值越小图像质量越低，图片占用空间越小
        """
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        cv2.imencode('.jpeg', img, params=params)[1].tofile(filepath)

    @classmethod
    def compress_image(cls, img_path: str, ratio: float = 0.5, quality=80, out_img_path: str = None):
        """
        @func 压缩图像, 保存为jpeg格式
        @param img_path: 需要压缩的图片地址
        @param ratio: 分辨率压缩比例范围0~1, 数值越小输出分辨率越低, 图片占用空间越小
        @param quality: jpeg图像质量, 范围0~100, 数值越小图像质量越低，图片占用空间越小
        @param out_img_path: 输出图片路径, 当设置为None时使用img_path作为输出图片路径，即在原图片上修改
        """
        pic = cls.imread(img_path)
        height, width, deep = pic.shape
        width, height = (width * ratio, height * ratio)
        pic = cv2.resize(pic, (int(width), int(height)))
        if out_img_path is None:
            out_img_path = img_path
        cls.imwrite(pic, out_img_path, quality)

    @classmethod
    def crop_image(cls, img_path: str, area: Rect, out_img_path: str = None):
        """
        @func 裁剪图片
        @param img_path: 需要裁剪的图片路径
        @param area: 需要裁剪的区域, 使用Rect类型指定
        """
        img = cls.imread(img_path)
        height, width = img.shape[0], img.shape[1]
        if area.left < 0 or area.right > width or area.top < 0 or area.bottom > height:
            raise HypiumParamError("area", msg="area is not in image: %s, image size %s" % (str(area), (width, height)))
        img = img[area.top: area.bottom, area.left: area.right]
        if out_img_path is None:
            out_img_path = img_path
        cls.imwrite(img, out_img_path)

    @classmethod
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
                  image_bounds = CVBasic.find_image("target.jpeg", "background.jpeg")
        """
        im_target = cls.imread(target_image_path)
        im_src = cls.imread(background_image_path)
        # default match_point is 8
        if mode == "template":
            similarity = kwargs.get("similarity", 0.9)
            result = cv2.matchTemplate(im_target, im_src, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            hypium_inner_log.info("实际最大相似度为 %.2f, 期望相似度为 %.2f" % (max_val, similarity))
            if max_val >= similarity:
                height, width,  _ = im_target.shape
                rect = Rect(max_loc[0], max_loc[0] + width, max_loc[1], max_loc[1] + height)
            else:
                return None
        elif mode == "sift":
            result = find_image_by_sift(im_src, im_target, **kwargs)
            if result is None:
                return None
            result = result[0]
            rect = result['rectangle']
        else:
            raise HypiumParamError(msg="invalid mode [%s], expect [template, sift]" % mode)
        return rect

    @classmethod
    def compare_image(cls, image_path_a: str, image_path_b: str, mode: str = "template", with_color: bool = False) -> float:
        """
        @func 比较两张图片的相似度
        @param image_path_a: 第一张图片
        @param image_path_b: 第二张图片
        @param mode: 比较算法, "template" 表示相关系数算法比较, "sift"表示特征点算法比较
        @return 图片相似度0~1,, 数字越大相似度越高
        """
        img1 = cls.imread(image_path_a)
        img2 = cls.imread(image_path_b)
        if with_color:
            similarities = []
            for i in range(3):
                img1_color = img1[:, :, i]
                img2_color = img2[:, :, i]
                result = cv2.matchTemplate(img1_color, img2_color, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                similarities.append(max_val)
            result = np.mean(similarities)
            return float(result)

        gray_img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray_img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        height, width = gray_img1.shape
        gray_img2 = cv2.resize(gray_img2, (width, height))
        if mode == "template":
            result = cv2.matchTemplate(gray_img1, gray_img2, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        elif mode == "sift":
            max_val = compare_image_by_sift(gray_img1, gray_img2)
        else:
            raise HypiumParamError(msg="invalid mode [%s], expect [template, sift]" % mode)
        return max_val

    @classmethod
    def calculate_clarity(cls, image_path: str) -> float:
        """
        @func 计算图像的清晰度(通过检测图像中物体轮廓清晰度实现, 无法用于纯色的图片)
        @return 代表图像清晰度的数值, 值越大表示图像越清晰, 内容不同的图片使用该方法计算出的清晰度
                不具备绝对的可比性, 内容相同的图片计算出的清晰度具有可比性。
        """
        image = cls.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian

    @classmethod
    def calculate_brightness(cls, image_path: str):
        """
        @func 计算图像的平均亮度
        """
        image = cls.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean = np.mean(gray)
        return mean

    @classmethod
    def encode_qr_code(cls, content: str, save_path: str):
        """
        @func 生成二维码
        @param content: 需要保存的二维码中的字符串
        @param save_path: 生成的二维码图片保存路径
        """
        try:
            import qrcode
        except Exception as e:
            raise RuntimeError("please install qrcode with pip first: pip install qrcode")
        qr = qrcode.QRCode(version=1, box_size=10, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(content)
        qr.make(fit=True)
        qr_img = qr.make_image()
        qr_img.save(save_path)

    @classmethod
    def decode_qr_code(cls, image_path: str) -> str:
        """
        @func 解析二维码
        @param image_path: 二维码图片路径
        @return 二维码图片中的文本信息, 如果解析二维码失败则返回空字符串
        """
        try:
            from pyzbar import pyzbar
        except Exception as e:
            raise RuntimeError("please install pyzbar with pip first: pip install pyzbar")
        img = CVBasic.imread(image_path)
        result = pyzbar.decode(img, symbols=[pyzbar.ZBarSymbol.QRCODE])
        if len(result) == 0:
            return ""
        else:
            return result[0].data.decode(encoding="utf-8", errors="ignore")

    @classmethod
    def get_video_resolution(cls, file_path: str) -> (int, int):
        """
        @func 读取视频分辨率
        @file_path PC端视频文件路径
        @return 视频分辨率, (宽度, 高度)
        @example # 获取视频分辨率
                 resolution = CVBasic.get_video_resolution("test.mp4")
        """
        cap = cv2.VideoCapture(file_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # 释放资源
        cap.release()
        return width, height

