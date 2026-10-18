# ============================================================
# 工具层：通用工具函数
# 作用：封装和业务无关的通用能力，所有项目都可以复用
# ============================================================

import random
import re
import time
from datetime import datetime, timedelta

# 日志里需要脱敏的字段名（统一小写比较）
SENSITIVE_KEYS = ("password", "token", "authorization", "cookie", "set-cookie")
MASK = "***"


class Utils:
    @staticmethod
    def random_string(length=8):
        """生成随机字符串"""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(random.choices(chars, k=length))

    @staticmethod
    def random_int(min_val=1, max_val=1000):
        """生成随机整数"""
        return random.randint(min_val, max_val)

    @staticmethod
    def random_price():
        """生成随机价格（1-1000的整数）"""
        return random.randint(1, 1000)

    @staticmethod
    def random_date():
        """生成随机日期字符串（YYYY-MM-DD），范围 2024-01-01 起两年内"""
        base = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 730))
        return base.strftime("%Y-%m-%d")

    @staticmethod
    def add_days(date_str, days):
        """
        在指定日期上加 N 天，返回 YYYY-MM-DD

        用途：生成入住/离店日期时保证 checkout 一定晚于 checkin，
        避免出现"离店早于入住"这种业务上不可能的数据
        """
        day = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)
        return day.strftime("%Y-%m-%d")

    @staticmethod
    def mask_mapping(data):
        """对字典里的敏感字段脱敏（如登录密码、token），用于日志输出"""
        if not isinstance(data, dict):
            return data

        masked = {}
        for key, value in data.items():
            if str(key).lower() in SENSITIVE_KEYS:
                masked[key] = MASK
            elif isinstance(value, dict):
                masked[key] = Utils.mask_mapping(value)
            else:
                masked[key] = value
        return masked

    @staticmethod
    def mask_text(text):
        """对 JSON 文本里的敏感字段脱敏（用于打印响应体），非字符串原样返回"""
        if not isinstance(text, str):
            return text

        pattern = r'("(?:password|token|authorization|cookie|set-cookie)"\s*:\s*")([^"]*)(")'
        return re.sub(
            pattern,
            lambda m: m.group(1) + MASK + m.group(3),
            text,
            flags=re.IGNORECASE,
        )

    @staticmethod
    def random_booking_data():
        """
        生成随机的预订数据
        对应 restful-booker 创建预订的请求体格式

        注意：checkin 先随机，checkout 在 checkin 基础上加 1~7 天，
        保证"离店晚于入住"，否则就是业务上不合理的数据
        """
        firstnames = ["张三", "李四", "王五", "赵六", "钱七", "Alice", "Bob", "Charlie"]
        lastnames = ["张", "李", "王", "赵", "钱", "Smith", "Johnson", "Williams"]

        checkin = Utils.random_date()
        checkout = Utils.add_days(checkin, random.randint(1, 7))

        return {
            "firstname": random.choice(firstnames),
            "lastname": random.choice(lastnames),
            "totalprice": Utils.random_price(),
            "depositpaid": random.choice([True, False]),
            "bookingdates": {
                "checkin": checkin,
                "checkout": checkout,
            },
            "additionalneeds": random.choice(["早餐", "停车位", "WiFi", "加床", None]),
        }

    @staticmethod
    def now_time_str(format="%Y-%m-%d %H:%M:%S"):
        """获取当前时间字符串"""
        return datetime.now().strftime(format)

    @staticmethod
    def timestamp():
        """获取当前时间戳（秒）"""
        return int(time.time())


# 实例化
utils = Utils()
