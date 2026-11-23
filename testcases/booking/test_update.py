# ============================================================
# 用例层：修改预订接口测试（共 8 条）
#   TestBookingPut    4 条：全量修改、缺字段 400、id 不存在 405、幂等
#   TestBookingPatch  4 条：局部修改、bookingdates 覆盖缺陷、id 不存在 405、幂等
#
# PUT 与 PATCH 的差异（实测确认）：
#   - PUT 会走 validator，缺必填字段返回 400（POST 同样情况返回 500，码不统一）
#   - PATCH 完全不校验，直接 Object.assign(doc, body)，只做顶层合并：
#       传 {"bookingdates": {"checkin": "..."}} 会把整个 bookingdates 替换掉，
#       checkout 丢失后在响应阶段格式化成 "0NaN-aN-aN"
# ============================================================

import allure
import pytest

from api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

update_data = data_loader.load("booking/update.yaml")


@allure.feature("预订管理")
@allure.story("修改预订")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.booking
class TestBookingPut:
    """PUT 全量修改"""

    @allure.title("PUT 全量修改并落库")
    @pytest.mark.smoke
    def test_put_full_update(self, make_booking):
        booking_id, _ = make_booking()
        new_data = update_data["put"]

        res = booking_api.update_booking(booking_id, new_data)
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_response_time(res, label=f"PUT /booking/{booking_id}")

        body = res.json()
        assert_utils.assert_field_value(body, "firstname", new_data["firstname"])
        assert_utils.assert_field_value(body, "lastname", new_data["lastname"])
        assert_utils.assert_field_value(body, "totalprice", new_data["totalprice"])
        assert_utils.assert_field_value(body["bookingdates"], "checkin", new_data["bookingdates"]["checkin"])

        # 响应正确不代表落库正确，再查一次
        detail = booking_api.get_booking_detail(booking_id).json()
        assert_utils.assert_field_value(detail, "firstname", new_data["firstname"])
        assert_utils.assert_field_value(detail["bookingdates"], "checkout", new_data["bookingdates"]["checkout"])

    @allure.title("PUT 缺少必填字段返回 400")
    @allure.description("同一个校验在 POST 上返回 500、在 PUT 上返回 400，状态码不统一")
    def test_put_missing_field(self, make_booking):
        booking_id, _ = make_booking()
        res = booking_api.update_booking(booking_id, {"firstname": "只有名字"})
        assert_utils.assert_status_code(res, 400)

    @allure.title("PUT 不存在的 ID 返回 405")
    @allure.description("注意不是 404：GET 查不到返回 404，PUT 改不到返回 405")
    def test_put_not_found(self, admin_login):
        res = booking_api.update_booking(999999, update_data["put"])
        assert_utils.assert_status_code(res, 405)

    @allure.title("PUT 幂等：同一份请求体连续两次结果一致")
    @pytest.mark.idempotency
    def test_put_idempotent(self, make_booking):
        booking_id, _ = make_booking()
        new_data = update_data["put"]

        first = booking_api.update_booking(booking_id, new_data)
        second = booking_api.update_booking(booking_id, new_data)

        assert_utils.assert_status_code(first, 200)
        assert_utils.assert_status_code(second, 200)
        with allure.step("断言：两次 PUT 的响应体完全一致"):
            assert first.json() == second.json(), \
                f"PUT 应幂等，两次响应不一致：{first.json()} vs {second.json()}"

        detail = booking_api.get_booking_detail(booking_id).json()
        assert_utils.assert_field_value(detail, "totalprice", new_data["totalprice"])


@allure.feature("预订管理")
@allure.story("修改预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingPatch:
    """PATCH 局部修改"""

    @allure.title("PATCH 只改一个字段，其余字段保持不变")
    @pytest.mark.smoke
    def test_patch_partial_field(self, make_booking):
        booking_id, original = make_booking()
        patch = update_data["patch"]

        res = booking_api.patch_booking(booking_id, patch)
        assert_utils.assert_status_code(res, 200)

        body = res.json()
        assert_utils.assert_field_value(body, "firstname", patch["firstname"])
        # 局部更新的核心断言：没传的字段不能被清空或改动
        assert_utils.assert_field_value(body, "lastname", original["lastname"])
        assert_utils.assert_field_value(body, "totalprice", original["totalprice"])
        assert_utils.assert_field_value(
            body["bookingdates"], "checkin", original["bookingdates"]["checkin"]
        )

    @allure.title("PATCH 只传 bookingdates.checkin 会覆盖整个对象")
    @allure.description("Object.assign 是顶层合并，checkout 丢失后回显为 0NaN-aN-aN（缺陷）")
    def test_patch_bookingdates_overwrites(self, make_booking):
        booking_id, _ = make_booking(
            bookingdates={"checkin": "2026-03-10", "checkout": "2026-03-15"}
        )

        res = booking_api.patch_booking(booking_id, {"bookingdates": {"checkin": "2026-07-01"}})
        assert_utils.assert_status_code(res, 200)

        dates = res.json()["bookingdates"]
        assert_utils.assert_field_value(dates, "checkin", "2026-07-01")
        assert_utils.assert_field_value(dates, "checkout", "0NaN-aN-aN")

    @allure.title("PATCH 不存在的 ID 返回 405")
    def test_patch_not_found(self, admin_login):
        res = booking_api.patch_booking(999999, {"firstname": "无此人"})
        assert_utils.assert_status_code(res, 405)

    @allure.title("PATCH 幂等：同一份请求体连续两次结果一致")
    @pytest.mark.idempotency
    def test_patch_idempotent(self, make_booking):
        booking_id, _ = make_booking()
        patch = {"firstname": "重复改"}

        first = booking_api.patch_booking(booking_id, patch)
        second = booking_api.patch_booking(booking_id, patch)

        assert_utils.assert_status_code(first, 200)
        assert_utils.assert_status_code(second, 200)
        with allure.step("断言：两次 PATCH 的响应体完全一致"):
            assert first.json() == second.json(), \
                f"PATCH 应幂等，两次响应不一致：{first.json()} vs {second.json()}"
