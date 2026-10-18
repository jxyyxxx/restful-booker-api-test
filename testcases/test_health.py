# ============================================================
# 用例层：健康检查
# 覆盖：/ping 返回 201、响应时间在门禁内
# 说明：这是冒烟集的第一条，用来确认被测服务真的在线，
#      服务没起来时这里会先红，而不是让后面几十条用例集体报连接错误
# ============================================================

import allure
import pytest
from common.assert_utils import assert_utils
from common.http_client import http


@allure.feature("健康检查")
@allure.story("/ping")
@pytest.mark.smoke
class TestHealth:
    """被测服务健康检查"""

    @allure.title("/ping 返回 201，服务在线")
    @allure.description(
        "restful-booker 的 /ping 是探活接口，成功时返回 201（不是 200），"
        "响应体为 Created；本用例同时校验响应时间门禁"
    )
    def test_ping(self):
        """GET /ping 应返回 201"""
        res = http.get("/ping")
        assert_utils.assert_status_code(res, 201)
        assert_utils.assert_response_time(res, label="GET /ping")
