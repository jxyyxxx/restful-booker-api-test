# ============================================================
# 夹具层：全局公共 fixture 统一放这里
# 作用：封装公共前置/后置逻辑、公共资源
#      所有测试文件不需要 import，直接就能用里面的 fixture
# ============================================================

import os
import platform
import shutil
import subprocess
import pytest
from common.api.auth_api import auth_api
from common.api.booking_api import booking_api
from common.allure_report import set_default_language
from common.http_client import http
from common.logger import logger
from common.utils import utils
from config.settings import BASE_URL, ADMIN_USER, ADMIN_PWD, ENV, RESPONSE_TIME_LIMIT


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
    token = auth_api.get_token(ADMIN_USER, ADMIN_PWD)

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
# 5. 写 Allure 报告的环境面板与失败分类
#    注意：必须在 CI 提前返回之前执行——CI 里报告由 workflow 生成，
#    同样需要 results 目录里的 environment.properties 和 categories.json
# ------------------------------------------------------------
def _write_allure_metadata(session):
    """
    往 reports/allure-results 写两份元数据：

    1. environment.properties —— Allure 报告左侧「环境」面板的数据源，
       会显示被测地址、Python/pytest 版本、操作系统，以及本次执行范围
    2. categories.json —— 失败分类规则，报告里的「分类」页靠它把失败归到
       「断言失败 / 响应时间门禁超限 / 被测服务不可用」

    执行范围是自动推断的：pytest 的 -m 表达式存在就记为 filtered/smoke，
    没有 -m/-k 就记为 full，所以冒烟跑和全量跑在报告里能直接区分开。
    """
    results_dir = "reports/allure-results"
    os.makedirs(results_dir, exist_ok=True)

    # 本次执行范围：-m smoke → smoke；无过滤 → full；其他表达式 → filtered
    markexpr = (getattr(session.config.option, "markexpr", "") or "").strip()
    keyword = (getattr(session.config.option, "keyword", "") or "").strip()
    if not markexpr and not keyword:
        scope = "full"
    elif markexpr in ("smoke", "booking", "auth", "regression"):
        scope = markexpr
    elif markexpr:
        scope = "filtered"
    else:
        scope = "filtered"

    lines = [
        ("env", ENV),
        ("base_url", BASE_URL),
        ("scope", scope),
        ("markexpr", markexpr or "(none)"),
        ("keyword", keyword or "(none)"),
        ("collected", str(session.testscollected)),
        ("python", platform.python_version()),
        ("pytest", pytest.__version__),
        ("os", platform.platform()),
        ("response_time_limit_s", f"{RESPONSE_TIME_LIMIT:g}"),
    ]
    with open(os.path.join(results_dir, "environment.properties"), "w", encoding="utf-8") as f:
        for key, value in lines:
            f.write(f"{key}={value}\n")

    # 失败分类：仓库里维护规则，跑测试时拷进结果目录
    categories_src = os.path.join("config", "allure_categories.json")
    if os.path.exists(categories_src):
        shutil.copyfile(categories_src, os.path.join(results_dir, "categories.json"))


# ------------------------------------------------------------
# 6. pytest 钩子：测试会话结束后自动生成 Allure 报告并打开
# ------------------------------------------------------------
def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束后自动执行：
    1. 写入 Allure 报告的环境面板与失败分类（本地和 CI 都需要）
    2. 调用 allure generate 生成 HTML 报告并打开（仅本地）

    CI 环境下跳过第 2 步：GitHub Actions 没有浏览器可开，且 workflow 里已经显式
    执行了一次 allure generate，这里再生成一遍只会拖慢流水线、还可能写坏同一份报告。
    """
    _write_allure_metadata(session)

    if os.getenv("CI"):
        logger.info("检测到 CI 环境，跳过本地 allure generate / allure open，报告由 workflow 生成")
        return

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

    # 报告默认语言设为中文（CI 里由 workflow 的同名步骤完成）
    if set_default_language(report_dir):
        logger.info("报告默认语言已设为中文，打开即中文界面")
    else:
        logger.warning("报告结构不符，跳过默认语言设置")

    # 自动打开浏览器（用 allure open 启动本地 HTTP 服务，避免 file:// 协议加载失败）
    if os.path.exists(report_index):
        logger.info("正在打开报告...")
        subprocess.Popen(
            f'allure open {report_dir}',
            shell=True
        )
    else:
        logger.warning("报告文件不存在，无法自动打开")
