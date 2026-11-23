# ============================================================
# 用例层：创建预订接口测试（共 17 条）
#   TestBookingCreate         9 条：数据驱动的正向/缺必填字段（500）
#   TestBookingContentType    3 条：XML / 表单 / Accept 非法（418）
#   TestBookingDataEdge       4 条：trim、无业务校验、类型错误、非法日期
#   TestBookingNotIdempotent  1 条：同一份 body 连发两次得到两条记录
#
# 服务端行为（已实测确认，断言按实际行为写，差异本身就是缺陷）：
#   - 校验只用 validate.js 的 presence，只拦 null/undefined，不拦 ""/0/false
#   - 校验失败返回 500（PUT 同样情况返回 400）
#   - 不校验日期合法性：非法日期会被存下，回显成 "0NaN-aN-aN"
#   - totalprice 用 parseInt 回显，传字符串会变成 null
#   - 无业务校验：checkout 早于 checkin 也能创建成功
#   - Accept 非法时返回 418，但记录**已经写入**（创建与响应解析不在一个事务里）
# ============================================================

import re

import allure
import pytest

from api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_factory import data_factory
from common.data_loader import data_loader

booking_create_data, booking_create_ids = data_loader.get_test_data("booking/create.yaml")


def _booking_id_of(res):
    """从创建响应里取 bookingid，取不到返回 None（失败时用于兜底清理）"""
    if res.status_code != 200:
        return None
    try:
        return res.json().get("bookingid")
    except ValueError:
        return None


def _delete_quiet(booking_id):
    if booking_id:
        booking_api.delete_booking(booking_id)


@allure.feature("预订管理")
@allure.story("创建预订")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.booking
class TestBookingCreate:
    """创建预订：数据驱动的正向与缺字段场景"""

    @allure.title("创建预订")
    @allure.description("创建预订接口参数化测试，覆盖正向和缺少必填字段")
    @pytest.mark.parametrize("case", booking_create_data, ids=booking_create_ids)
    def test_create_booking(self, admin_login, case):
        # 参数化传的是整个 dict，@allure.title 的占位符取不到内部字段，只能运行时设置
        allure.dynamic.title(f"创建预订-{case['case_name']}")

        res = booking_api.create_booking(case["data"])
        try:
            assert_utils.assert_status_code(res, case["expected_code"])
            assert_utils.assert_response_time(res, label="POST /booking")

            if case["expected_code"] == 200:
                assert_utils.assert_create_booking_success(res, case["data"])
        finally:
            # 数据自动回收：断言失败也照样执行，否则每跑一轮就往系统里堆数据
            _delete_quiet(_booking_id_of(res))


@allure.feature("预订管理")
@allure.story("创建预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingContentType:
    """创建预订：内容协商（请求体格式与响应格式）"""

    XML_BODY = (
        "<booking>"
        "<firstname>Xml</firstname><lastname>Probe</lastname>"
        "<totalprice>9</totalprice><depositpaid>true</depositpaid>"
        "<bookingdates><checkin>2026-04-01</checkin><checkout>2026-04-02</checkout></bookingdates>"
        "</booking>"
    )
    FORM_BODY = (
        "firstname=Form&lastname=Probe&totalprice=77&depositpaid=true"
        "&bookingdates%5Bcheckin%5D=2026-06-01&bookingdates%5Bcheckout%5D=2026-06-03"
    )

    @allure.title("XML 请求体创建预订")
    @allure.description("Content-Type: text/xml 可创建；响应是 XML，但 Content-Type 仍为 text/html（已知缺陷）")
    def test_create_with_xml(self, admin_login):
        res = booking_api.create_booking_raw(self.XML_BODY, "text/xml", "application/xml")
        booking_id = None
        try:
            assert_utils.assert_status_code(res, 200)
            assert_utils.assert_body_contains(res, "<created-booking>")
            assert_utils.assert_body_contains(res, "<firstname>Xml</firstname>")
            # 服务端直接 res.send(字符串)，Content-Type 没有被设置成 application/xml
            assert_utils.assert_content_type(res, "text/html")
            matched = re.search(r"<bookingid>(\d+)</bookingid>", res.text)
            if matched:
                booking_id = int(matched.group(1))
        finally:
            _delete_quiet(booking_id)

    @allure.title("表单请求体创建预订")
    @allure.description("Content-Type: application/x-www-form-urlencoded 可创建，响应按 Accept 返回 JSON")
    def test_create_with_form(self, admin_login):
        res = booking_api.create_booking_raw(
            self.FORM_BODY, "application/x-www-form-urlencoded", "application/json"
        )
        booking_id = _booking_id_of(res)
        try:
            assert_utils.assert_status_code(res, 200)
            assert_utils.assert_content_type(res, "application/json")
            assert_utils.assert_field_value(res.json()["booking"], "firstname", "Form")
        finally:
            _delete_quiet(booking_id)

    @allure.title("Accept 非法返回 418，但数据已落库")
    @allure.description("服务端先写库再解析响应，解析失败返回 418，记录却留在库里（缺少事务）")
    def test_create_invalid_accept_keeps_data(self, admin_login):
        before = {item["bookingid"] for item in booking_api.get_booking_list().json()}
        res = booking_api.create_booking(
            data_factory.random_booking_data(), headers={"Accept": "text/html"}
        )
        after = {item["bookingid"] for item in booking_api.get_booking_list().json()}
        new_ids = after - before
        try:
            assert_utils.assert_status_code(res, 418)
            assert len(new_ids) == 1, (
                f"预期 418 时数据已写入（服务端缺少事务），实际新增 {len(new_ids)} 条：{new_ids}"
            )
        finally:
            for booking_id in new_ids:
                _delete_quiet(booking_id)


@allure.feature("预订管理")
@allure.story("创建预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingDataEdge:
    """创建预订：数据处理与缺失校验的边界"""

    @allure.title("姓名首尾空格被 trim 后入库")
    def test_create_trims_names(self, make_booking):
        booking_id, _ = make_booking(firstname="  张三  ", lastname=" 李四 ")
        body = booking_api.get_booking_detail(booking_id).json()
        assert_utils.assert_field_value(body, "firstname", "张三")
        assert_utils.assert_field_value(body, "lastname", "李四")

    @allure.title("checkout 早于 checkin 仍创建成功")
    @allure.description("服务端没有业务规则校验，离店早于入住也能入库")
    def test_create_checkout_before_checkin(self, make_booking):
        booking_id, _ = make_booking(
            bookingdates={"checkin": "2026-05-10", "checkout": "2026-05-01"}
        )
        body = booking_api.get_booking_detail(booking_id).json()
        assert_utils.assert_field_value(body["bookingdates"], "checkin", "2026-05-10")
        assert_utils.assert_field_value(body["bookingdates"], "checkout", "2026-05-01")

    @allure.title("totalprice 传字符串：校验通过，回显为 null")
    @allure.description("presence 只拦 null/undefined；parseInt('abc') 得 NaN，JSON 里变成 null")
    def test_create_totalprice_as_string(self, admin_login):
        payload = data_factory.random_booking_data()
        payload["totalprice"] = "abc"
        res = booking_api.create_booking(payload)
        booking_id = _booking_id_of(res)
        try:
            assert_utils.assert_status_code(res, 200)
            assert res.json()["booking"]["totalprice"] is None, \
                f"预期 totalprice 回显为 null，实际 {res.json()['booking']['totalprice']!r}"
        finally:
            _delete_quiet(booking_id)

    @allure.title("非法日期：校验通过，回显为 0NaN-aN-aN")
    @allure.description("服务端不校验日期格式，格式化阶段得到 Invalid Date 但仍以字符串写回")
    def test_create_invalid_date(self, admin_login):
        payload = data_factory.random_booking_data()
        payload["bookingdates"] = {"checkin": "2024-13-45", "checkout": "2024-13-50"}
        res = booking_api.create_booking(payload)
        booking_id = _booking_id_of(res)
        try:
            assert_utils.assert_status_code(res, 200)
            booking = res.json()["booking"]
            assert_utils.assert_field_value(booking["bookingdates"], "checkin", "0NaN-aN-aN")
            assert_utils.assert_field_value(booking["bookingdates"], "checkout", "0NaN-aN-aN")
        finally:
            _delete_quiet(booking_id)


@allure.feature("预订管理")
@allure.story("创建预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
@pytest.mark.idempotency
class TestBookingNotIdempotent:
    """创建预订：POST 不是幂等操作"""

    @allure.title("同一份请求体提交两次生成两条记录")
    def test_same_body_creates_two_bookings(self, admin_login):
        payload = data_factory.random_booking_data()

        first = booking_api.create_booking(payload)
        second = booking_api.create_booking(payload)
        first_id, second_id = _booking_id_of(first), _booking_id_of(second)

        try:
            assert_utils.assert_status_code(first, 200)
            assert_utils.assert_status_code(second, 200)
            assert first_id != second_id, f"POST 应非幂等，两次却返回同一个 id={first_id}"
            # 两条都能独立查到，说明确实是两条独立记录
            assert_utils.assert_status_code(booking_api.get_booking_detail(first_id), 200)
            assert_utils.assert_status_code(booking_api.get_booking_detail(second_id), 200)
        finally:
            _delete_quiet(first_id)
            _delete_quiet(second_id)
