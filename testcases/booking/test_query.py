# ============================================================
# 用例层：预订查询接口测试（列表 10 条 + 详情 9 条）
#
# 两条设计原则：
#   1. 正向用例自己造数据（make_booking），不依赖服务启动时的种子数据——
#      否则换一种启动方式（没设 SEED=true）就会整条报 404
#   2. 过滤类用例只断言"自己那条在不在结果里"，不断言结果总数——
#      库里还有别的数据，断言总数会让用例互相干扰
#
# 过滤参数的实现与官方文档不一致（已实测确认），用例按**实际行为**断言，
# 并在描述里写明差异，这些差异本身就是被测服务的缺陷：
#   - 文档写 checkin >= 入参，实际是 $gt（同日数据被排除）
#   - 文档写 checkout >= 入参，实际是 $lt（早于入参的数据反而被包含）
# ============================================================

import allure
import pytest
from api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

# 从 YAML 文件读取详情查询的反向数据（0 / 负数 / 超大值 / 非数字）
booking_query_data, booking_query_ids = data_loader.get_test_data("booking/query.yaml")


@allure.feature("预订管理")
@allure.story("查询预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingList:
    """查询预订列表：结构与四个过滤参数"""

    @allure.title("查询预订列表")
    @allure.description("先创建一条预订再查列表，验证结构、非空，且新建的那条确实在列表里")
    @pytest.mark.smoke
    def test_booking_list(self, test_booking):
        """查询预订列表（自建数据，不依赖种子数据）"""
        res = booking_api.get_booking_list()
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_response_time(res, label="GET /booking")

        body = res.json()
        assert_utils.assert_is_list(body)
        assert_utils.assert_list_not_empty(body)

        # 列表只返回 bookingid：结构断言一次就够，不要对每条重复断言（同一条规则说 N 遍没有信息量）
        with allure.step(f"断言：列表内每条记录结构为 {{bookingid}}（共 {len(body)} 条）"):
            bad = [i for i, item in enumerate(body) if set(item.keys()) != {"bookingid"}]
            assert not bad, f"第 {bad[:3]} 条结构异常，示例：{body[bad[0]]}"

        assert_utils.assert_list_contains_id(body, test_booking)

    @allure.title("按 firstname 精确过滤")
    def test_filter_firstname_hit(self, make_booking):
        """firstname 是精确等值匹配（不是模糊搜索）"""
        booking_id, data = make_booking(firstname="筛选甲")
        res = booking_api.get_booking_list(params={"firstname": "筛选甲"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_is_list(res.json())
        assert_utils.assert_list_contains_id(res.json(), booking_id)

    @allure.title("按 firstname 过滤区分大小写")
    @allure.description("服务端用等值匹配，firstname 不转小写，所以大小写不同应查不到")
    def test_filter_firstname_case_sensitive(self, make_booking):
        booking_id, _ = make_booking(firstname="FilterCase")
        res = booking_api.get_booking_list(params={"firstname": "filtercase"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_not_contains_id(res.json(), booking_id)

    @allure.title("按 lastname 精确过滤")
    def test_filter_lastname_hit(self, make_booking):
        booking_id, _ = make_booking(lastname="筛选乙")
        res = booking_api.get_booking_list(params={"lastname": "筛选乙"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_contains_id(res.json(), booking_id)

    @allure.title("按 lastname 过滤无匹配时返回空列表")
    @allure.description("无匹配应返回 200 + []，而不是 404")
    def test_filter_lastname_no_match(self, make_booking):
        booking_id, _ = make_booking(lastname="筛选丙")
        res = booking_api.get_booking_list(params={"lastname": "肯定不存在的姓"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_is_list(res.json())
        assert_utils.assert_list_not_contains_id(res.json(), booking_id)

    @allure.title("按 checkin 过滤：同日数据不被包含")
    @allure.description("文档写 checkin >= 入参，实际实现是 $gt，同日创建的数据会被排除")
    def test_filter_checkin_same_day_excluded(self, make_booking):
        booking_id, _ = make_booking(
            bookingdates={"checkin": "2026-03-10", "checkout": "2026-03-15"}
        )
        res = booking_api.get_booking_list(params={"checkin": "2026-03-10"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_not_contains_id(res.json(), booking_id)

    @allure.title("按 checkin 过滤：入参早于入住日期时被包含")
    def test_filter_checkin_before_included(self, make_booking):
        booking_id, _ = make_booking(
            bookingdates={"checkin": "2026-03-10", "checkout": "2026-03-15"}
        )
        res = booking_api.get_booking_list(params={"checkin": "2026-03-09"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_contains_id(res.json(), booking_id)

    @allure.title("按 checkout 过滤：同日数据被包含")
    def test_filter_checkout_same_day_included(self, make_booking):
        booking_id, _ = make_booking(
            bookingdates={"checkin": "2026-03-10", "checkout": "2026-03-15"}
        )
        res = booking_api.get_booking_list(params={"checkout": "2026-03-15"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_contains_id(res.json(), booking_id)

    @allure.title("按 checkout 过滤：入参晚于离店日期时仍被包含（实现与文档不符）")
    @allure.description("文档要求 checkout >= 入参，实际是 $lt，离店早于入参的数据反而被包含")
    def test_filter_checkout_later_boundary(self, make_booking):
        booking_id, _ = make_booking(
            bookingdates={"checkin": "2026-03-10", "checkout": "2026-03-15"}
        )
        res = booking_api.get_booking_list(params={"checkout": "2026-03-16"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_contains_id(res.json(), booking_id)

    @allure.title("组合过滤 firstname + lastname")
    def test_filter_combined(self, make_booking):
        booking_id, _ = make_booking(firstname="组合甲", lastname="组合乙")
        res = booking_api.get_booking_list(params={"firstname": "组合甲", "lastname": "组合乙"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_list_contains_id(res.json(), booking_id)

    @allure.title("列表接口不处理内容协商，Accept 非法仍返回 JSON")
    @allure.description("列表接口直接 res.send 数组，不看 Accept；与详情接口非法 Accept 返回 418 形成对照")
    def test_booking_list_ignores_accept(self, test_booking):
        res = booking_api.get_booking_list(headers={"Accept": "text/html"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_content_type(res, "application/json")
        assert_utils.assert_is_list(res.json())


@allure.feature("预订管理")
@allure.story("查询预订")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.booking
class TestBookingDetail:
    """查询预订详情：正向、id 解析缺陷、内容协商、反向数据"""

    @allure.title("查询刚创建的预订详情")
    @allure.description("自建一条预订并查询它，断言 200 与核心字段，不依赖种子数据")
    def test_booking_detail_own_data(self, make_booking):
        booking_id, data = make_booking()
        res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_response_time(res, label=f"GET /booking/{booking_id}")

        body = res.json()
        assert_utils.assert_booking_fields(body)
        # 除了字段存在，还要比对回显值，否则服务端返回别人的数据也能过
        assert_utils.assert_field_value(body, "firstname", data["firstname"])
        assert_utils.assert_field_value(body, "totalprice", data["totalprice"])

    @allure.title("id 带小数时按 parseInt 截断（12.9 → 12）")
    @allure.description("服务端用 parseInt(id)，所以带小数的 ID 会命中整数那条记录，属于解析缺陷")
    def test_booking_detail_id_with_decimal(self, make_booking):
        booking_id, data = make_booking()
        res = booking_api.get_booking_detail(f"{booking_id}.9")
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_field_value(res.json(), "firstname", data["firstname"])

    @allure.title("id 带前导零仍能命中（0012 → 12）")
    def test_booking_detail_id_leading_zero(self, make_booking):
        booking_id, data = make_booking()
        res = booking_api.get_booking_detail(f"00{booking_id}")
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_field_value(res.json(), "firstname", data["firstname"])

    @allure.title("详情支持 XML 响应")
    @allure.description("Accept: application/xml 时返回 XML；注意服务端 Content-Type 仍是 text/html（已知缺陷）")
    def test_booking_detail_accept_xml(self, make_booking):
        booking_id, data = make_booking()
        res = booking_api.get_booking_detail(booking_id, headers={"Accept": "application/xml"})
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_body_contains(res, "<?xml")
        assert_utils.assert_body_contains(res, f"<firstname>{data['firstname']}</firstname>")

    @allure.title("详情响应不含 bookingid 字段")
    @allure.description("列表返回 bookingid、详情只返回业务字段，两者结构不同，容易误判")
    def test_booking_detail_without_bookingid(self, make_booking):
        booking_id, _ = make_booking()
        res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_field_absent(res.json(), "bookingid")

    @allure.title("查询预订详情（不存在的 ID）")
    @allure.description("覆盖 ID=0、负数、超大值、非数字，预期 404")
    @pytest.mark.parametrize("test_data", booking_query_data, ids=booking_query_ids)
    def test_booking_detail_not_found(self, test_data):
        """查询不存在的预订详情，预期 404"""
        allure.dynamic.title(f"查询预订详情-{test_data['case_name']}")

        booking_id = test_data["booking_id"]
        expected_code = test_data["expected_code"]

        res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(res, expected_code)
        assert_utils.assert_response_time(res, label=f"GET /booking/{booking_id}")
