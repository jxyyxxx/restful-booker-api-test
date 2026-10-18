# ============================================================
# 用例层：创建预订接口测试
# 覆盖：完整数据创建、缺少可选字段、缺少必填字段
# ============================================================

import allure
import pytest
from common.api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

# 从 YAML 文件读取创建预订测试数据
booking_create_data, booking_create_ids = data_loader.get_test_data("booking/create_data.yaml")


@allure.feature("预订管理")
@allure.story("创建预订")
@pytest.mark.booking
class TestBookingCreate:
    """创建预订接口测试"""

    @allure.title("创建预订")
    @allure.description("创建预订接口测试，覆盖正向和反向用例")
    @pytest.mark.parametrize("case", booking_create_data, ids=booking_create_ids)
    def test_create_booking(self, admin_login, case):
        """创建预订接口测试，覆盖正向和反向用例"""
        # 动态设置 Allure 报告标题：原因同 test_auth.py，占位符取不到 dict 内部字段
        allure.dynamic.title(f"创建预订-{case['case_name']}")

        res = booking_api.create_booking(case["data"])
        try:
            assert_utils.assert_status_code(res, case["expected_code"])

            # 成功时验证创建结果
            if case["expected_code"] == 200:
                assert_utils.assert_create_booking_success(res, case["data"])
        finally:
            # 数据自动回收：创建成功的预订在用例结束时删除（断言失败也照样执行）
            # 不清理的话每跑一轮就往系统里堆 9 条左右预订，
            # GET /booking 的响应体会越来越大，后续用例和性能测试都会被污染
            booking_id = None
            if res.status_code == 200:
                try:
                    booking_id = res.json().get("bookingid")
                except ValueError:
                    booking_id = None
            if booking_id:
                booking_api.delete_booking(booking_id)
