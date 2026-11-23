# ============================================================
# 用例层：预订接口权限测试（共 5 条）
#
# 服务端认证方式有两种，任选其一即可通过：
#   1. Cookie: token=<15 位 hex>（/auth 返回）
#   2. Authorization: Basic YWRtaW46cGFzc3dvcmQxMjM=
#      —— 代码里是写死的字符串比较，并没有真正解析用户名密码
#
# 只作用于 PUT / PATCH / DELETE；未认证一律 403（不是 401）。
# 全局 Session 带着有效 token，所以用例里用 anonymous / invalid_token 夹具
# 临时摘掉或替换凭证，结束后自动恢复。
# ============================================================

import allure
import pytest

from api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

update_data = data_loader.load("booking/update.yaml")

# admin:password123 的 Base64，服务端直接按这个常量比对
BASIC_AUTH = "Basic YWRtaW46cGFzc3dvcmQxMjM="


@allure.feature("预订管理")
@allure.story("接口权限")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.booking
class TestBookingPermission:
    """PUT / PATCH / DELETE 的认证要求"""

    @allure.title("无 token 修改预订返回 403")
    def test_put_without_token(self, make_booking, anonymous):
        booking_id, _ = make_booking()
        res = booking_api.update_booking(booking_id, update_data["put"])
        assert_utils.assert_status_code(res, 403)

    @allure.title("无 token 局部修改返回 403")
    def test_patch_without_token(self, make_booking, anonymous):
        booking_id, _ = make_booking()
        res = booking_api.patch_booking(booking_id, {"firstname": "未认证"})
        assert_utils.assert_status_code(res, 403)

    @allure.title("无 token 删除预订返回 403")
    def test_delete_without_token(self, make_booking, anonymous):
        booking_id, _ = make_booking()
        res = booking_api.delete_booking(booking_id)
        assert_utils.assert_status_code(res, 403)

        # 数据必须还在：403 不能真的把记录删掉
        assert_utils.assert_status_code(booking_api.get_booking_detail(booking_id), 200)

    @allure.title("无效 token 删除预订返回 403")
    def test_delete_with_invalid_token(self, make_booking, invalid_token):
        booking_id, _ = make_booking()
        res = booking_api.delete_booking(booking_id)
        assert_utils.assert_status_code(res, 403)

    @allure.title("Basic 认证可修改预订")
    @allure.description("不依赖 Cookie，仅凭 Authorization: Basic 头也能通过认证")
    def test_put_with_basic_auth(self, make_booking, anonymous):
        booking_id, _ = make_booking()
        res = booking_api.update_booking(
            booking_id, update_data["put"], headers={"Authorization": BASIC_AUTH}
        )
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_field_value(res.json(), "firstname", update_data["put"]["firstname"])
