# ============================================================
# 用例层：修改预订接口测试
# 覆盖：PUT 全量修改、PATCH 部分修改
# ============================================================

import allure
from common.api.booking_api import booking_api
from common.assert_utils import assert_utils


@allure.feature("预订管理")
@allure.story("修改预订")
class TestBookingUpdate:
    """修改预订接口测试"""

    @allure.title("全量修改预订（PUT）")
    @allure.description("使用PUT方法全量修改预订，验证修改成功且数据正确")
    def test_update_booking(self, admin_login, test_booking):
        """
        修改预订接口测试（PUT 全量修改）
        admin_login：确保已登录，token 自动存入 Cookie
        test_booking：自动创建测试预订，返回 bookingid，用例后自动删除
        """
        booking_id = test_booking
        update_data = {
            "firstname": "修改后的名字",
            "lastname": "修改后的姓",
            "totalprice": 999,
            "depositpaid": False,
            "bookingdates": {"checkin": "2025-01-01", "checkout": "2025-01-10"},
            "additionalneeds": "豪华套餐"
        }

        res = booking_api.update_booking(booking_id, update_data)
        assert_utils.assert_status_code(res, 200)

        # 验证修改后的数据
        res_json = res.json()
        assert_utils.assert_field_value(res_json, "firstname", "修改后的名字")
        assert_utils.assert_field_value(res_json, "totalprice", 999)
        assert_utils.assert_field_value(res_json, "additionalneeds", "豪华套餐")

    @allure.title("部分修改预订（PATCH）")
    @allure.description("使用PATCH方法只修改部分字段，验证修改的字段更新，未修改的字段保持不变")
    def test_patch_booking(self, admin_login, test_booking):
        """
        部分修改预订接口测试（PATCH）
        只修改 firstname 和 totalprice，其他字段保持不变
        """
        booking_id = test_booking

        # 先查询原始数据
        original_res = booking_api.get_booking_detail(booking_id)
        original_data = original_res.json()

        # 只修改两个字段
        patch_data = {
            "firstname": "PATCH修改的名字",
            "totalprice": 888
        }

        res = booking_api.patch_booking(booking_id, patch_data)
        assert_utils.assert_status_code(res, 200)

        # 验证修改的字段更新了
        res_json = res.json()
        assert_utils.assert_field_value(res_json, "firstname", "PATCH修改的名字")
        assert_utils.assert_field_value(res_json, "totalprice", 888)
        # 验证未修改的字段保持不变
        assert_utils.assert_field_value(res_json, "lastname", original_data["lastname"])
