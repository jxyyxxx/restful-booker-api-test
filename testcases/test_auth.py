# ============================================================
# 用例层：登录接口测试
# 覆盖：正向登录、密码错误、用户名为空、密码为空、用户名不存在、token格式
# ============================================================

import allure
import pytest
from common.api.auth_api import auth_api
from common.assert_utils import assert_utils
from common.data_loader import data_loader

# 从 YAML 文件读取登录测试数据，自动提取 case_name 作为用例名
login_data, login_ids = data_loader.get_test_data("auth/login_data.yaml")


@allure.feature("登录认证")
@allure.story("登录接口")
class TestAuth:
    """登录接口测试"""

    @allure.title("登录测试-{case_name}")
    @allure.description("登录接口参数化测试，覆盖正向和反向场景")
    @pytest.mark.parametrize("test_data", login_data, ids=login_ids)
    def test_login(self, test_data):
        """
        登录接口参数化测试
        覆盖：正向登录、密码错误、用户名为空、密码为空、用户名不存在
        """
        # 从测试数据字典中取值
        username = test_data["username"]
        password = test_data["password"]
        expected_code = test_data["expected_code"]
        expected_success = test_data["expected_success"]
        case_name = test_data["case_name"]

        # 1. 调用登录接口
        res = auth_api.login(username, password)

        # 2. 断言状态码
        assert_utils.assert_status_code(res, expected_code)

        # 3. 断言登录结果
        res_json = res.json()
        if expected_success:
            # 预期成功：响应里应该有 token 字段
            assert_utils.assert_field_exists(res_json, "token")
            assert res_json["token"] != "", f"登录失败，token 为空：{res_json}"
        else:
            # 预期失败：响应里应该有 reason 字段
            assert_utils.assert_field_exists(res_json, "reason")

    @allure.title("验证登录成功返回的token格式")
    @allure.description("正向登录，验证返回的 token 长度和格式正确")
    def test_login_success_token_format(self):
        """正向登录，验证返回的 token 格式正确"""
        res = auth_api.login("admin", "password123")
        assert_utils.assert_status_code(res, 200)

        res_json = res.json()
        assert_utils.assert_field_exists(res_json, "token")

        token = res_json["token"]
        # restful-booker 的 token 是 15 位左右的随机字符串
        assert len(token) >= 10, f"token 长度异常：{len(token)}"
        assert token.isalnum(), f"token 格式异常，应为字母数字组合：{token}"
