# ============================================================
# 工具层：Allure 报告相关（元数据、生成、默认语言）
#
# 原来拆在两个地方：
#   - common/allure_report.py：只负责默认语言
#   - conftest.py：环境面板、失败分类、生成与打开
# 现在统一到这里，conftest 只保留 pytest 钩子的注册。
#
# 命令行用法（CI 里单独调）：
#   python -m common.reporting allure-report            # 设置默认语言为中文
#   python -m common.reporting <dir> --lang en          # 需要时切回英文
# ============================================================

import argparse
import os
import platform
import shutil
import subprocess

import pytest

from common.logger import logger
from config.settings import BASE_URL, ENV, RESPONSE_TIME_LIMIT

# 结果目录与报告目录（与 pytest.ini 的 --alluredir 保持一致）
RESULTS_DIR = "reports/allure-results"
REPORT_DIR = "reports/allure-html"

# 失败分类规则的仓库内路径（跑测试时拷进结果目录）
CATEGORIES_SRC = os.path.join("config", "allure", "categories.json")

# ---- 默认语言注入 ----------------------------------------------------------
MARKER = "<!-- allure-default-language -->"

SCRIPT_TEMPLATE = (
    MARKER + "\n"
    "<script>\n"
    "  try {\n"
    "    var k = 'ALLURE_REPORT_SETTINGS';\n"
    "    var s = JSON.parse(localStorage.getItem(k) || '{}');\n"
    "    s.language = '__LANG__';\n"
    "    localStorage.setItem(k, JSON.stringify(s));\n"
    "  } catch (e) {\n"
    "    /* 浏览器隐私模式禁用 localStorage 时忽略，报告仍可正常打开 */\n"
    "  }\n"
    "</script>\n"
)

APP_JS_ANCHOR = '<script src="app.js"></script>'


def set_default_language(report_dir, lang="zh"):
    """
    往 Allure 报告的 index.html 注入"默认语言"脚本（幂等）

    原理：报告前端的语言选择存在 localStorage 的 ALLURE_REPORT_SETTINGS.language，
    默认是 en；在 app.js 之前先写成 zh，打开即中文。

    :param report_dir: 报告目录（含 index.html）
    :param lang: 语言代码，中文用 zh
    :return: True 表示已设置或已存在；False 表示目录/结构不匹配
    """
    index_path = os.path.join(report_dir, "index.html")
    if not os.path.exists(index_path):
        return False

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 幂等：已经注入过就不重复写
    if MARKER in html:
        return True

    if APP_JS_ANCHOR not in html:
        return False

    script = SCRIPT_TEMPLATE.replace("__LANG__", lang)
    html = html.replace(APP_JS_ANCHOR, "    " + script + "    " + APP_JS_ANCHOR, 1)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    return True


# ---- 环境面板 + 失败分类 ----------------------------------------------------
def write_allure_metadata(session):
    """
    往 reports/allure-results 写两份元数据：

    1. environment.properties —— Allure 报告左侧「环境」面板的数据源，
       会显示被测地址、Python/pytest 版本、操作系统，以及本次执行范围
    2. categories.json —— 失败分类规则，报告里的「分类」页靠它把失败归到
       「响应时间门禁超限 / 被测服务不可用 / 断言失败」

    执行范围是自动推断的：pytest 的 -m 表达式存在就记为 filtered/smoke，
    没有 -m/-k 就记为 full，所以冒烟跑和全量跑在报告里能直接区分开。

    必须在 CI 提前返回之前调用——CI 里报告由 workflow 生成，
    同样需要 results 目录里的这两个文件。
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)

    markexpr = (getattr(session.config.option, "markexpr", "") or "").strip()
    keyword = (getattr(session.config.option, "keyword", "") or "").strip()

    if not markexpr and not keyword:
        scope = "full"
    elif markexpr in ("smoke", "booking", "auth", "regression"):
        scope = markexpr
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
    with open(os.path.join(RESULTS_DIR, "environment.properties"), "w", encoding="utf-8") as f:
        for key, value in lines:
            f.write(f"{key}={value}\n")

    if os.path.exists(CATEGORIES_SRC):
        shutil.copyfile(CATEGORIES_SRC, os.path.join(RESULTS_DIR, "categories.json"))


# ---- 本地生成报告 ----------------------------------------------------------
def generate_local_report(results_dir=RESULTS_DIR, report_dir=REPORT_DIR):
    """
    本地跑完测试后生成 Allure 报告、设中文、打开浏览器

    CI 里不要调用：workflow 会显式执行 allure generate，且没有浏览器可开。

    :return: True 表示报告已生成
    """
    report_index = os.path.join(report_dir, "index.html")

    if not shutil.which("allure"):
        logger.warning("未检测到 allure 命令行工具，跳过报告生成")
        return False

    logger.info("正在生成 Allure 报告...")
    try:
        subprocess.run(
            f'allure generate {results_dir} -o {report_dir} --clean',
            shell=True,
            check=True,
            capture_output=True,
        )
        logger.info(f"Allure 报告已生成：{report_index}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Allure 报告生成失败：{e}")
        return False

    if set_default_language(report_dir):
        logger.info("报告默认语言已设为中文，打开即中文界面")
    else:
        logger.warning("报告结构不符，跳过默认语言设置")

    # 用 allure open 起本地服务，避免 file:// 协议下数据加载失败
    if os.path.exists(report_index):
        logger.info("正在打开报告...")
        subprocess.Popen(f'allure open {report_dir}', shell=True)
    else:
        logger.warning("报告文件不存在，无法自动打开")

    return True


def main(argv=None):
    """CI 里单独调用：把已生成的报告默认语言设为中文"""
    parser = argparse.ArgumentParser(description="设置 Allure 报告的默认语言")
    parser.add_argument("report_dir", help="报告目录，例如 allure-report 或 reports/allure-html")
    parser.add_argument("--lang", default="zh", help="语言代码，默认 zh")
    args = parser.parse_args(argv)

    if set_default_language(args.report_dir, args.lang):
        print("已设置默认语言 %s：%s" % (args.lang, args.report_dir))
        return 0

    print("跳过（报告目录不存在或 index.html 结构不符）：%s" % args.report_dir)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
