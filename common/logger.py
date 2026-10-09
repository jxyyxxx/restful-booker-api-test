# ============================================================
# 日志工具类
# 作用：统一日志格式，同时输出到控制台和文件，方便排查问题
# 优化点：单例模式、级别可配置、格式含定位信息、异常堆栈记录、文件名含环境标识
# ============================================================

import logging
import os
from datetime import datetime
from config.settings import ENV, LOG_CONFIG


class Logger:
    """日志工具类（单例模式，全局只有一个实例）"""

    _instance = None  # 单例实例

    def __new__(cls, *args, **kwargs):
        """单例模式：确保全局只有一个 Logger 实例，避免重复创建 handler 和日志文件"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir=None):
        """
        初始化日志
        :param log_dir: 日志文件存放目录，不传则用配置文件里的
        """
        # 单例模式下，只初始化一次
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.log_dir = log_dir or LOG_CONFIG["log_dir"]
        self._ensure_dir()
        self.logger = self._create_logger()
        self._initialized = True  # 标记已初始化

    def _ensure_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _get_level(self, level_str):
        """把字符串级别转成 logging 常量"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return level_map.get(level_str.upper(), logging.INFO)

    def _create_logger(self):
        """创建 logger 实例"""
        logger = logging.getLogger("api_test")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()  # 清除已有 handler，避免重复输出

        # 日志格式（从配置读取，含模块名/函数名/行号，方便定位问题）
        formatter = logging.Formatter(
            LOG_CONFIG["log_format"],
            datefmt=LOG_CONFIG["date_format"]
        )

        # 控制台输出（级别从配置读取）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._get_level(LOG_CONFIG["console_level"]))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件输出（按时间命名，文件名含环境标识，方便区分多环境日志）
        # 格式：{环境}_{时间}.log，例如 local_2026-09-09_15-30-00.log
        log_file = os.path.join(
            self.log_dir,
            f"{ENV}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(self._get_level(LOG_CONFIG["file_level"]))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def info(self, message):
        """普通信息"""
        self.logger.info(message, stacklevel=2)

    def error(self, message):
        """错误信息"""
        self.logger.error(message, stacklevel=2)

    def debug(self, message):
        """调试信息"""
        self.logger.debug(message, stacklevel=2)

    def warning(self, message):
        """警告信息"""
        self.logger.warning(message, stacklevel=2)

    def exception(self, message):
        """
        异常信息（自动记录完整堆栈 traceback）
        用法：在 except 块里调用 logger.exception("出错了")，会自动把异常堆栈打出来
        """
        self.logger.exception(message, stacklevel=2)

    def separator(self, title=""):
        """打印分隔线，方便区分不同用例"""
        if title:
            self.info(f"========== {title} ==========")
        else:
            self.info("=" * 50)


# 全局实例，其他模块直接导入使用
logger = Logger()
