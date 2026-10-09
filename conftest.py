# ============================================================
# 夹具层：全局公共 fixture 统一放这里
# 作用：封装公共前置/后置逻辑、公共资源
#      所有测试文件不需要 import，直接就能用里面的 fixture
# ============================================================

import os
import shutil
import subprocess
import pytest
from common.api.auth_api import auth_api
from common.api.booking_api import booking_api
from common.http_client import http
from common.logger import logger
from common.utils import utils
from config.settings import ENV_CONFIG, ENV


# ------------------------------------------------------------
# 1. 环境健康检查：autouse=True，所有测试自动执行
#    scope="session"：整个测试会话只执行1次
# ------------------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def check_env_health():
    """测试开始前自动检查服务是否正常"""
    logger.separator("开始环境健康检查")
    logger.info(f"当前环境：{ENV}")
    logger.info(f"接口地址：{ENV_CONFIG[ENV]['base_url']}")
    logger.separator()
    yield
    logger.separator("全部测试执行完毕")


# ------------------------------------------------------------
# 2. 每个用例的开始/结束日志：autouse=True，自动执行
#    scope="function"：每个测试函数执行1次
# ------------------------------------------------------------
@pytest.fixture(autouse=True, scope="function")
def log_test_case(request):
    """自动记录每个用例的开始和结束"""
    logger.separator(f"开始执行用例：{request.node.name}")
    yield
    logger.info(f"用例执行完成：{request.node.name}")


# ------------------------------------------------------------
# 3. 管理员登录：全局只登录1次，所有用例共享
#    scope="session"：整个测试会话只执行1次
#    restful-booker 登录后 token 放在 Cookie 里，Session 自动管理
# ------------------------------------------------------------
@pytest.fixture(scope="session")
def admin_login():
    """
    管理员登录，返回 token
    整个测试会话只执行1次，避免重复登录
    登录后 token 自动存入 Session 的 Cookie，后续请求自动带上
    """
    logger.info("执行管理员登录...")
    token = auth_api.get_token(
        ENV_CONFIG[ENV]["admin_user"],
        ENV_CONFIG[ENV]["admin_pwd"]
    )

    # 把 token 存入 Session 的 Cookie，后续请求自动带上
    # restful-booker 的认证方式是 Cookie: token=xxx
    http.session.cookies.set("token", token)

    logger.info(f"登录成功，获取到 token：{token}")
    return token


# ------------------------------------------------------------
# 4. 测试预订数据：每条用例前创建，用例后自动删除
#    scope="function"：每个测试函数执行1次
#    使用 yield 实现前置+后置一体
#    依赖 admin_login fixture，确保已登录（删除需要认证）
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def test_booking(admin_login):
    """
    每条用例前创建一篇测试预订，用例跑完自动删除
    实现测试数据的自动造数+自动清理
    返回创建的预订ID
    """
    # 前置：创建测试预订
    logger.info("前置：创建测试预订...")
    booking_data = utils.random_booking_data()
    res = booking_api.create_booking(booking_data)
    booking_id = res.json().get("bookingid")
    logger.info(f"测试预订创建成功，ID：{booking_id}")

    # 返回预订ID给测试用例，暂停等待用例执行
    yield booking_id

    # 后置：删除测试预订（用例执行完后一定会执行，哪怕用例失败）
    logger.info(f"后置：删除测试预订 ID={booking_id}...")
    booking_api.delete_booking(booking_id)
    logger.info("测试数据清理完成")


# ------------------------------------------------------------
# 5. pytest 钩子：测试会话结束后自动生成 Allure 报告并打开
# ------------------------------------------------------------
def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束后自动执行：
    1. 调用 allure generate 生成 HTML 报告
    2. 自动在浏览器中打开报告
    不管跑全部还是单个用例，结束后都会自动生成报告
    """
    results_dir = "reports/allure-results"
    report_dir = "reports/allure-html"
    report_index = os.path.join(report_dir, "index.html")

    # 检查 allure 命令是否可用
    allure_path = shutil.which("allure")
    if not allure_path:
        logger.warning("未检测到 allure 命令行工具，跳过报告生成")
        return

    # 生成报告
    logger.info("正在生成 Allure 报告...")
    try:
        subprocess.run(
            f'allure generate {results_dir} -o {report_dir} --clean',
            shell=True,
            check=True,
            capture_output=True
        )
        logger.info(f"Allure 报告已生成：{report_index}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Allure 报告生成失败：{e}")
        return

    # 自动打开浏览器（用 allure open 启动本地 HTTP 服务，避免 file:// 协议加载失败）
    if os.path.exists(report_index):
        logger.info("正在打开报告...")
        subprocess.Popen(
            f'allure open {report_dir}',
            shell=True
        )
    else:
        logger.warning("报告文件不存在，无法自动打开")
