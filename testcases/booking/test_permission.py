# ============================================================
# 用例层：预订接口权限测试（未认证 403）
# 覆盖：未认证时修改预订应该返回 403
# ============================================================

import allure
import pytest
from api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_factory import data_factory
from common.http_client import http
from common.logger import logger


@allure.feature("预订管理")
@allure.story("认证权限")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingPermission:
    """预订接口认证权限测试"""

    @allure.title("未登录时修改预订返回403")
    @allure.description("未登录状态下修改预订，验证接口返回403禁止访问")
    def test_update_without_auth(self, admin_login):
        """
        未登录时修改预订应该返回 403

        admin_login 一定要显式声明：本用例会临时清空 Session 的 Cookie，
        如果进用例时压根没登录过，original_cookies 就是空字典，
        finally 里既恢复不了登录态、也删不掉自己创建的数据，每跑一轮就泄漏一条预订。
        """
        # 先创建一条预订（创建接口不需要认证）
        create_data = data_factory.random_booking_data()
        create_res = booking_api.create_booking(create_data)
        booking_id = create_res.json()["bookingid"]

        # 临时保存并清除 Cookie，模拟未登录状态
        original_cookies = http.session.cookies.get_dict()
        http.session.cookies.clear()

        try:
            # 未登录修改应该失败
            res = booking_api.update_booking(booking_id, create_data)
            assert_utils.assert_status_code(res, 403)
            assert_utils.assert_response_time(res, label="PUT /booking/{id} 未认证")
        finally:
            # 恢复 Cookie（token 回来了，后面的删除才有权限）
            for key, value in original_cookies.items():
                http.session.cookies.set(key, value)

            # 清理测试数据：只记录结果、不 assert。
            # 这段在 finally 里，若 assert 失败会覆盖用例原本的失败原因，
            # 导致报告显示"清理失败"，而真正的 403 断言失败被藏起来
            delete_res = booking_api.delete_booking(booking_id)
            if delete_res.status_code != 201:
                logger.error(
                    f"测试数据清理失败，预订 ID={booking_id} 未删除，状态码：{delete_res.status_code}"
                )
