# ============================================================
# 用例层：预订接口认证测试
# 覆盖：未认证时修改/删除应该返回403
# ============================================================

import allure
from common.api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.http_client import http
from common.utils import utils


@allure.feature("预订管理")
@allure.story("认证权限")
class TestBookingAuth:
    """预订接口认证权限测试"""

    @allure.title("未登录时修改预订返回403")
    @allure.description("未登录状态下修改预订，验证接口返回403禁止访问")
    def test_update_without_auth(self):
        """未登录时修改预订应该返回403"""
        # 先创建一条预订
        create_data = utils.random_booking_data()
        create_res = booking_api.create_booking(create_data)
        booking_id = create_res.json()["bookingid"]

        # 临时清除 Cookie 模拟未登录
        original_cookies = http.session.cookies.get_dict()
        http.session.cookies.clear()

        try:
            # 未登录修改应该失败
            res = booking_api.update_booking(booking_id, create_data)
            assert_utils.assert_status_code(res, 403)
        finally:
            # 恢复 Cookie
            for key, value in original_cookies.items():
                http.session.cookies.set(key, value)
            # 清理测试数据
            booking_api.delete_booking(booking_id)
