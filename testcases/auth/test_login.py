# ============================================================
# 用例层：登录接口测试
# 覆盖：正向登录，以及密码错误/为空/空白、用户名不存在/为空/空白/带空格/大小写、null
# 说明：服务端对用户名密码做严格相等比较（不 trim、区分大小写），
#      失败时同样返回 200 + {"reason": "Bad credentials"}，所以反向用例的断言要点是
#      「状态码 200 + reason 正确 + 没有 token」；只断言 reason 存在会漏掉半个契约。
# ============================================================

import allure
import pytest
from api.auth_api import auth_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

# 从 YAML 文件读取登录测试数据，自动提取 case_name 作为用例名
login_data, login_ids = data_loader.get_test_data("auth/login.yaml")


@allure.feature("登录认证")
@allure.story("登录接口")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.auth
class TestLogin:
    """登录接口测试"""

    @allure.title("登录测试")
    @allure.description("登录接口参数化测试，覆盖正向和各类反向输入")
    @pytest.mark.parametrize("test_data", login_data, ids=login_ids)
    def test_login(self, test_data):
        """登录接口参数化测试"""
        username = test_data["username"]
        password = test_data["password"]
        expected_code = test_data["expected_code"]
        expected_success = test_data["expected_success"]

        # 参数化传进来的是整个 dict，@allure.title 的占位符取不到内部字段，只能运行时设置
        allure.dynamic.title(f"登录测试-{test_data['case_name']}")

        res = auth_api.login(username, password)
        assert_utils.assert_status_code(res, expected_code)

        res_json = res.json()
        if expected_success:
            assert_utils.assert_field_exists(res_json, "token")
            assert res_json["token"] != "", f"登录失败，token 为空：{res_json}"
        else:
            # 三个断言缺一不可：reason 存在、值正确、且绝不能带 token
            assert_utils.assert_field_exists(res_json, "reason")
            assert_utils.assert_field_value(res_json, "reason", "Bad credentials")
            assert_utils.assert_field_absent(res_json, "token")

    @allure.title("验证登录成功返回的token格式")
    @allure.description("正向登录，验证返回的 token 长度和格式正确")
    @pytest.mark.smoke
    def test_login_success_token_format(self):
        """正向登录，验证返回的 token 格式正确"""
        res = auth_api.login("admin", "password123")
        assert_utils.assert_status_code(res, 200)
        assert_utils.assert_response_time(res, label="POST /auth")

        res_json = res.json()
        assert_utils.assert_field_exists(res_json, "token")

        token = res_json["token"]
        # 服务端实现：randomBytes(8).toString('hex').slice(0, 15) → 定长 15 位十六进制
        assert len(token) == 15, f"token 长度异常：{len(token)}，预期 15"
        assert all(c in "0123456789abcdef" for c in token), f"token 应为十六进制字符串：{token}"
