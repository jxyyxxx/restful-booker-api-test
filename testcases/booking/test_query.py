# ============================================================
# 用例层：预订查询接口测试
# 覆盖：查询预订列表、查询预订详情（自建数据 + 各类不存在的 ID）
# 说明：正向用例自己造数据，不依赖被测服务的种子数据——
#      否则换一种启动方式（没设 SEED=true）就会整条报 404
# ============================================================

import allure
import pytest
from common.api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

# 从 YAML 文件读取查询预订测试数据（全部是"不存在/非法 ID"的反向数据）
booking_query_data, booking_query_ids = data_loader.get_test_data("booking/query_data.yaml")


@allure.feature("预订管理")
@allure.story("查询预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingQuery:
    """预订查询接口测试"""

    @allure.title("查询预订列表")
    @allure.description("先创建一条预订再查列表，验证返回的是列表、不为空，且每条数据都有 bookingid")
    @pytest.mark.smoke
    def test_booking_list(self, test_booking):
        """查询预订列表（自建数据，不依赖种子数据）"""
        res = booking_api.get_booking_list()
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_response_time(res, label="GET /booking")

        res_json = res.json()
        assert_utils.assert_is_list(res_json)
        assert_utils.assert_list_not_empty(res_json)

        # 验证每条数据都有 bookingid 字段
        for item in res_json:
            assert_utils.assert_field_exists(item, "bookingid")

    @allure.title("查询刚创建的预订详情")
    @allure.description("用 test_booking 夹具自建一条预订并查询它，断言 200 与核心字段，不依赖种子数据")
    def test_booking_detail_own_data(self, test_booking):
        """查询自己创建的预订详情（正向场景，不依赖种子数据）"""
        res = booking_api.get_booking_detail(test_booking)
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_response_time(res, label=f"GET /booking/{test_booking}")
        assert_utils.assert_booking_fields(res.json())

    @allure.title("查询预订详情（不存在的 ID）")
    @allure.description("覆盖 ID=0、负数、超大值、正常区间内不存在的 ID，预期 404")
    @pytest.mark.parametrize("test_data", booking_query_data, ids=booking_query_ids)
    def test_booking_detail(self, test_data):
        """查询不存在的预订详情，预期 404"""
        # 动态设置 Allure 报告标题：原因同 testcases/auth/test_login.py，占位符取不到 dict 内部字段
        allure.dynamic.title(f"查询预订详情-{test_data['case_name']}")

        booking_id = test_data["booking_id"]
        expected_code = test_data["expected_code"]

        res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(res, expected_code)
        assert_utils.assert_response_time(res, label=f"GET /booking/{booking_id}")

        # 成功时验证返回的预订详情有核心字段（当前数据全是 404，保留判断便于以后扩展）
        if expected_code == 200:
            assert_utils.assert_booking_fields(res.json())
