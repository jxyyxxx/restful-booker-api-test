# ============================================================
# 接口方法层：登录相关接口
# 作用：封装登录接口的调用，用例层只调方法，不关心地址和请求方式
# ============================================================

from common.http_client import http


class AuthAPI:
    """登录接口封装"""

    def login(self, username, password):
        """
        登录接口
        :param username: 用户名
        :param password: 密码
        :return: Response 对象
        """
        payload = {"username": username, "password": password}
        return http.post("/auth", json=payload)

    def get_token(self, username, password):
        """
        登录并获取 token
        :param username: 用户名
        :param password: 密码
        :return: token 字符串
        """
        res = self.login(username, password)
        return res.json().get("token")


# 全局实例，用例层直接导入使用
auth_api = AuthAPI()
