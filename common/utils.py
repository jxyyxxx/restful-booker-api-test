# ============================================================
# 工具层：通用工具函数
# 作用：封装和业务无关的通用能力，所有项目都可以复用
# ============================================================

import random
import time
from datetime import datetime


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
        """生成随机日期字符串（YYYY-MM-DD格式）"""
        year = random.randint(2024, 2026)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"

    @staticmethod
    def random_booking_data():
        """
        生成随机的预订数据
        对应 restful-booker 创建预订的请求体格式
        """
        firstnames = ["张三", "李四", "王五", "赵六", "钱七", "Alice", "Bob", "Charlie"]
        lastnames = ["张", "李", "王", "赵", "钱", "Smith", "Johnson", "Williams"]
        return {
            "firstname": random.choice(firstnames),
            "lastname": random.choice(lastnames),
            "totalprice": Utils.random_price(),
            "depositpaid": random.choice([True, False]),
            "bookingdates": {
                "checkin": Utils.random_date(),
                "checkout": Utils.random_date()
            },
            "additionalneeds": random.choice(["早餐", "停车位", "WiFi", "加床", None])
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
