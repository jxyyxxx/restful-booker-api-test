# ============================================================
# 用例层：预订查询接口测试
# 覆盖：查询预订列表、查询预订详情
# ============================================================

import allure
import pytest
from common.api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

# 从 YAML 文件读取查询预订测试数据
booking_query_data, booking_query_ids = data_loader.get_test_data("booking/query_data.yaml")


@allure.feature("预订管理")
@allure.story("查询预订")
class TestBookingQuery:
    """预订查询接口测试"""

    @allure.title("查询预订列表")
    @allure.description("验证查询预订列表接口返回正常，列表不为空，每条数据都有bookingid")
    def test_booking_list(self):
        """查询预订列表，验证返回的是列表且有数据"""
        res = booking_api.get_booking_list()
        assert_utils.assert_status_code(res, 200)

        res_json = res.json()
        assert_utils.assert_is_list(res_json)
        assert_utils.assert_list_not_empty(res_json)

        # 验证每条数据都有 bookingid 字段
        for item in res_json:
            assert_utils.assert_field_exists(item, "bookingid")

    @allure.title("查询预订详情-{case_name}")
    @allure.description("查询预订详情，覆盖正常ID和不存在的ID")
    @pytest.mark.parametrize("test_data", booking_query_data, ids=booking_query_ids)
    def test_booking_detail(self, test_data):
        """查询预订详情，覆盖正常ID和不存在的ID"""
        booking_id = test_data["booking_id"]
        expected_code = test_data["expected_code"]

        res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(res, expected_code)

        # 成功时验证返回的预订详情有核心字段
        if expected_code == 200:
            assert_utils.assert_booking_fields(res.json())
