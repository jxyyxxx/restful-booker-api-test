# ============================================================
# 工具层：HTTP 请求统一封装
# 作用：统一处理 base_url 拼接、超时、异常捕获、日志记录
#      使用 Session 自动管理 Cookie（登录后 token 自动带上）
# ============================================================

import time
import allure
import requests
from config.settings import BASE_URL, REQUEST_TIMEOUT
from common.logger import logger


class HttpClient:
    def __init__(self):
        # base_url 由配置层统一导出：环境变量 BASE_URL > local 默认值
        self.base_url = BASE_URL
        # 使用 Session 保持会话，自动管理 Cookie（登录后的 token 自动带上）
        self.session = requests.Session()

    def request(self, method, path, **kwargs):
        """
        统一请求方法
        :param method: 请求方式 GET/POST/PUT/PATCH/DELETE
        :param path: 接口路径（如 /auth, /booking），自动拼接 base_url
        :param kwargs: 其他参数（json, headers, params 等）
        :return: Response 对象
        """
        # 拼接完整 URL
        url = self.base_url + path

        # 设置默认超时时间
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)

        # 记录请求开始时间
        start_time = time.time()

        # 把这次调用包成一个 Allure 步骤：
        # 报告里会显示成 "POST /auth" 这样的节点，用例失败时能直接看出是哪个接口、
        # 哪一步出的问题，而不是只看到一个 assert 行号
        with allure.step(f"{method} {path}"):
            try:
                # 记录请求日志
                logger.info(f"发送请求：{method} {url}")
                if "json" in kwargs:
                    logger.debug(f"请求体：{kwargs['json']}")

                # 发送请求
                res = self.session.request(method, url, **kwargs)

                # 计算耗时
                elapsed = round(time.time() - start_time, 3)

                # 记录响应日志
                logger.info(f"响应状态码：{res.status_code}，耗时：{elapsed}s")
                logger.debug(f"响应体：{res.text[:500]}")

                return res
            except requests.exceptions.Timeout:
                logger.error(f"请求超时：{url}，超过 {REQUEST_TIMEOUT} 秒")
                raise
            except requests.exceptions.ConnectionError:
                logger.error(f"连接失败：{url}，请检查服务是否启动")
                raise
            except Exception as e:
                logger.error(f"请求异常：{e}")
                raise

    # 封装常用的五种请求方式，用例层直接调用
    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


# 实例化，用例层直接 from common.http_client import http 即可使用
http = HttpClient()
