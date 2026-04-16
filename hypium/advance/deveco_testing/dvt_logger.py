# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023. All rights reserved.

import logging
import os
from xdevice import platform_logger


deveco_log = platform_logger("DevecoTesting")


class SimpleFileLogger:

    def __init__(self, file_path: str):
        self.file_path = file_path

    def info(self, msg):
        if type(msg) != str:
            msg = str(msg)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(msg)
            f.write('\n')


class DvtLogger():
    log_path = ''
    loggers = dict()

    @classmethod
    def set_logger_path(cls, log_path: str) -> object:
        # 设置日志格式
        logging.basicConfig(
            filename=log_path,
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        DvtLogger.log_path = log_path
        logging.getLogger('').handlers[0].close()

        handler = logging.FileHandler(log_path)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger('').addHandler(handler)

    @classmethod
    def clear_log(cls):
        log_file = DvtLogger.log_path
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")

    @staticmethod
    def get_logger(name: str, file_path: str):
        if name not in DvtLogger.loggers.keys():
            dir_path = os.path.dirname(file_path)
            if (not os.path.exists(dir_path)) and len(dir_path) != 0:
                os.makedirs(dir_path)
            logger = SimpleFileLogger(file_path)
            DvtLogger.loggers[name] = logger
        return DvtLogger.loggers[name]


if __name__ == '__main__':
    DvtLogger.set_logger_path("a.log")
