# ============================================================
# 用例层：删除预订接口测试（共 5 条）
# 覆盖：删除成功、删除后详情 404、删除后列表不含、重复删除 405、删除不存在的 ID 405
#
# 服务端行为（实测确认）：
#   - 删除成功返回 201（不是 204）
#   - 重复删除 / id 不存在都返回 405（不是 404，也不是 200）
#   - 删除是幂等语义的"结果一致"：第一次成功、后续都 405，库里的状态不会再变
# ============================================================

import allure
import pytest

from api.booking_api import booking_api
from common.assert_utils import assert_utils


@allure.feature("预订管理")
@allure.story("删除预订")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.booking
class TestBookingDelete:
    """删除预订"""

    @allure.title("删除预订成功返回 201")
    @pytest.mark.smoke
    def test_delete_success(self, make_booking):
        booking_id, _ = make_booking()
        res = booking_api.delete_booking(booking_id)
        assert_utils.assert_status_code(res, 201)
        assert_utils.assert_response_time(res, label=f"DELETE /booking/{booking_id}")

    @allure.title("删除后查询详情返回 404")
    def test_delete_then_detail_not_found(self, make_booking):
        booking_id, _ = make_booking()
        assert_utils.assert_status_code(booking_api.delete_booking(booking_id), 201)

        res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(res, 404)

    @allure.title("删除后列表不再包含该 ID")
    def test_delete_then_list_excludes(self, make_booking):
        booking_id, _ = make_booking()
        assert_utils.assert_status_code(booking_api.delete_booking(booking_id), 201)

        res = booking_api.get_booking_list()
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_not_contains_id(res.json(), booking_id)

    @allure.title("重复删除返回 405")
    @pytest.mark.idempotency
    def test_delete_twice_returns_405(self, make_booking):
        booking_id, _ = make_booking()

        first = booking_api.delete_booking(booking_id)
        second = booking_api.delete_booking(booking_id)

        assert_utils.assert_status_code(first, 201)
        with allure.step("断言：第二次删除返回 405（数据已不存在）"):
            assert_utils.assert_status_code(second, 405)

    @allure.title("删除不存在的 ID 返回 405")
    def test_delete_not_found(self, admin_login):
        res = booking_api.delete_booking(999999)
        assert_utils.assert_status_code(res, 405)
