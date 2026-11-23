# ============================================================
# 断言工具类
# 作用：封装常用断言，统一报错信息，减少用例层重复代码
#      每个断言都包在 allure.step 里，报告里能直接看到"哪一步断言失败"
# ============================================================

import allure
from config.settings import RESPONSE_TIME_LIMIT


class AssertUtils:
    """断言工具类"""

    def assert_status_code(self, response, expected_code):
        """
        断言响应状态码
        :param response: requests Response 对象
        :param expected_code: 预期状态码
        """
        with allure.step(f"断言：状态码 == {expected_code}"):
            actual = response.status_code
            assert actual == expected_code, \
                f"状态码不符：预期 {expected_code}，实际 {actual}"

    def assert_response_time(self, response, max_seconds=None, label=""):
        """
        响应时间门禁：单次请求耗时必须小于阈值

        作用：接口测试通常只校验"对不对"，这里补上"快不快"，
        让功能用例也能拦住明显的性能劣化（如某次改动让接口从 5ms 涨到 800ms）。

        :param response: requests Response 对象
        :param max_seconds: 自定义阈值（秒）；不传则用配置里的 RESPONSE_TIME_LIMIT
        :param label: 失败时用于定位的接口说明，如 "GET /booking"
        """
        limit = max_seconds if max_seconds is not None else RESPONSE_TIME_LIMIT
        elapsed = response.elapsed.total_seconds()

        if label:
            target = label
        else:
            try:
                target = f"{response.request.method} {response.url}"
            except Exception:
                target = response.url

        with allure.step(f"断言：响应时间 < {limit * 1000:.0f}ms（实测 {elapsed * 1000:.0f}ms）"):
            assert elapsed < limit, (
                f"响应时间超限：{target} 耗时 {elapsed * 1000:.0f}ms，"
                f"超过阈值 {limit * 1000:.1f}ms"
            )

    def assert_field_exists(self, data, field_name):
        """
        断言字典中存在某个字段
        :param data: 字典数据
        :param field_name: 字段名
        """
        with allure.step(f"断言：响应包含字段 {field_name}"):
            assert field_name in data, f"响应缺少字段：{field_name}"

    def assert_field_value(self, data, field_name, expected_value):
        """
        断言字典中某个字段的值
        :param data: 字典数据
        :param field_name: 字段名
        :param expected_value: 预期值
        """
        with allure.step(f"断言：字段 {field_name} == {expected_value!r}"):
            actual = data.get(field_name)
            assert actual == expected_value, \
                f"字段 {field_name} 值不符：预期 {expected_value}，实际 {actual}"

    def assert_field_absent(self, data, field_name):
        """
        断言字典中不存在某个字段（如登录失败时不能出现 token）
        :param data: 字典数据
        :param field_name: 字段名
        """
        with allure.step(f"断言：响应不包含字段 {field_name}"):
            assert field_name not in data, f"响应不应包含字段 {field_name}，实际：{data}"

    def assert_is_list(self, data):
        """断言数据是列表类型"""
        with allure.step("断言：响应是列表"):
            assert isinstance(data, list), \
                f"响应应该是列表，实际是 {type(data).__name__}"

    def assert_list_not_empty(self, data):
        """断言列表不为空"""
        with allure.step("断言：列表不为空"):
            assert len(data) > 0, "列表不应该为空"

    def assert_list_empty(self, data):
        """断言列表为空（过滤无匹配时应返回 []，而不是 404 或 null）"""
        with allure.step("断言：列表为空"):
            assert isinstance(data, list), f"响应应该是列表，实际是 {type(data).__name__}"
            assert len(data) == 0, f"列表应该为空，实际有 {len(data)} 条"

    def assert_list_contains_id(self, data, booking_id):
        """断言列表里包含指定 bookingid（列表接口只返回 id，所以按 id 比对）"""
        with allure.step(f"断言：列表包含 bookingid={booking_id}"):
            ids = [item.get("bookingid") for item in data]
            assert booking_id in ids, f"列表中没有 {booking_id}，前 5 条：{ids[:5]}"

    def assert_list_not_contains_id(self, data, booking_id):
        """断言列表里不含指定 bookingid（用于过滤/删除后的反向验证）"""
        with allure.step(f"断言：列表不包含 bookingid={booking_id}"):
            ids = [item.get("bookingid") for item in data]
            assert booking_id not in ids, f"列表不应包含 {booking_id}，实际前 5 条：{ids[:5]}"

    def assert_body_contains(self, response, text):
        """断言响应体包含指定文本（XML / 表单等非 JSON 响应用）"""
        with allure.step(f"断言：响应体包含 {text!r}"):
            assert text in response.text, \
                f"响应体不含 {text!r}，实际前 200 字符：{response.text[:200]!r}"

    def assert_content_type(self, response, expected_prefix):
        """断言 Content-Type 前缀，例如 application/json、text/html"""
        with allure.step(f"断言：Content-Type 以 {expected_prefix} 开头"):
            actual = response.headers.get("Content-Type", "")
            assert actual.startswith(expected_prefix), \
                f"Content-Type 不符：预期 {expected_prefix}*，实际 {actual}"

    def assert_booking_fields(self, data):
        """
        断言预订详情包含核心字段（组合断言）
        :param data: 预订详情字典
        """
        with allure.step("断言：预订详情包含核心字段"):
            self.assert_field_exists(data, "firstname")
            self.assert_field_exists(data, "lastname")
            self.assert_field_exists(data, "totalprice")
            self.assert_field_exists(data, "bookingdates")

    def assert_create_booking_success(self, response, input_data):
        """
        断言创建预订成功（组合断言）
        :param response: 响应对象
        :param input_data: 传入的创建数据
        """
        with allure.step("断言：创建预订成功且回显数据一致"):
            self.assert_status_code(response, 200)
            res_json = response.json()
            self.assert_field_exists(res_json, "bookingid")
            self.assert_field_exists(res_json, "booking")
            # 验证创建的数据和传入的一致
            self.assert_field_value(res_json["booking"], "firstname", input_data["firstname"])
            self.assert_field_value(res_json["booking"], "totalprice", input_data["totalprice"])


# 全局实例，用例层直接导入使用
assert_utils = AssertUtils()
