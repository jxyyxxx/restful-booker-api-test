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
class TestBookingCreate:
    """创建预订接口测试"""

    @allure.title("创建预订-{case_name}")
    @allure.description("创建预订接口测试，覆盖正向和反向用例")
    @pytest.mark.parametrize("case", booking_create_data, ids=booking_create_ids)
    def test_create_booking(self, case):
        """创建预订接口测试，覆盖正向和反向用例"""
        res = booking_api.create_booking(case["data"])
        assert_utils.assert_status_code(res, case["expected_code"])

        # 成功时验证创建结果
        if case["expected_code"] == 200:
            assert_utils.assert_create_booking_success(res, case["data"])
