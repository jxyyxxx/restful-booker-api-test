# ============================================================
# 夹具层：全局公共 fixture 统一放这里
# 作用：封装公共前置/后置逻辑、公共资源
#      所有测试文件不需要 import，直接就能用里面的 fixture
#
# 报告相关（环境面板、失败分类、生成与打开）在 common/reporting.py，
# 这里只负责在 pytest 钩子里调用它。
# ============================================================

import os

import pytest

from api.auth_api import auth_api
from api.booking_api import booking_api
from common.data_factory import data_factory
from common.http_client import http
from common.logger import logger
from common.reporting import generate_local_report, write_allure_metadata
from config.settings import ADMIN_PWD, ADMIN_USER


# ------------------------------------------------------------
# 0. 收集阶段：把健康检查（/ping）提到最前面
#    目的：服务没起来时先红在探活这一条上，而不是让后面 30 多条用例
#    集体报连接错误；全量与冒烟集都生效
# ------------------------------------------------------------
def pytest_collection_modifyitems(session, config, items):
    # 按模块路径匹配（testcases/health/），不要再按文件名匹配——改名时一并同步
    health = [item for item in items if "/health/" in item.nodeid]
    if health:
        rest = [item for item in items if item not in health]
        items[:] = health + rest


# ------------------------------------------------------------
# 1. 每个用例的开始/结束日志：autouse=True，自动执行
#    scope="function"：每个测试函数执行1次
# ------------------------------------------------------------
@pytest.fixture(autouse=True, scope="function")
def log_test_case(request):
    """自动记录每个用例的开始和结束"""
    logger.separator(f"开始执行用例：{request.node.name}")
    yield
    logger.info(f"用例执行完成：{request.node.name}")


# ------------------------------------------------------------
# 2. 管理员登录：全局只登录1次，所有用例共享
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
    token = auth_api.get_token(ADMIN_USER, ADMIN_PWD)

    # restful-booker 的认证方式是 Cookie: token=xxx
    http.session.cookies.set("token", token)

    logger.info("登录成功，已写入 Session Cookie")
    return token


# ------------------------------------------------------------
# 3. 测试预订数据：每条用例前创建，用例后自动删除
#    scope="function"，yield 实现前置 + 后置一体
#    依赖 admin_login fixture，确保已登录（删除需要认证）
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def test_booking(admin_login):
    """
    每条用例前创建一条测试预订，用例跑完自动删除
    实现测试数据的自动造数 + 自动清理
    返回创建的预订 ID
    """
    logger.info("前置：创建测试预订...")
    booking_data = data_factory.random_booking_data()
    res = booking_api.create_booking(booking_data)
    booking_id = res.json().get("bookingid")
    logger.info(f"测试预订创建成功，ID：{booking_id}")

    yield booking_id

    # 用例执行完后一定会执行（哪怕用例失败）
    logger.info(f"后置：删除测试预订 ID={booking_id}...")
    booking_api.delete_booking(booking_id)
    logger.info("测试数据清理完成")


# ------------------------------------------------------------
# 4. 会话结束：写报告元数据 + 本地生成报告
# ------------------------------------------------------------
def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束后：
    1. 写入环境面板与失败分类（本地和 CI 都需要）
    2. 本地生成 Allure 报告、设中文、打开浏览器

    CI 里跳过第 2 步：workflow 已显式生成报告，且没有浏览器可开；
    在其他 CI（Jenkins 等）上跑请设置 CI=true。
    """
    write_allure_metadata(session)

    if os.getenv("CI"):
        logger.info("检测到 CI 环境，跳过本地 allure generate / allure open，报告由 workflow 生成")
        return

    generate_local_report()
