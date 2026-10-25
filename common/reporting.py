# ============================================================
# 工具层：Allure 报告相关（环境面板、失败分类、运行器、历史趋势、生成与默认语言）
#
# conftest.py 只负责在 pytest 钩子里调用这里的函数，具体实现都在这里。
#
# 命令行用法（CI 里单独调）：
#   python -m common.reporting allure-report            # 设置默认语言为中文
#   python -m common.reporting <dir> --lang en          # 需要时切回英文
# ============================================================

import argparse
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime

import pytest

from common.logger import logger
from config.settings import BASE_URL, ENV, RESPONSE_TIME_LIMIT, ROOT_DIR

# 结果目录与报告目录（与 pytest.ini 的 --alluredir 保持一致）
RESULTS_DIR = "reports/allure-results"
REPORT_DIR = "reports/allure-html"

# 失败分类规则的仓库内路径（跑测试时拷进结果目录）
CATEGORIES_SRC = os.path.join("config", "allure", "categories.json")

# 历史（趋势）的仓库内位置。必须放在结果目录之外：
# pytest.ini 的 --clean-alluredir 每次会话开始都会清空结果目录，
# 历史若放在结果目录里，每跑一次就被清掉，趋势图永远只有一个点。
# 按执行范围分目录存放（full / smoke / booking / auth ...），
# 避免"全量 40 条"和"冒烟 6 条"混成一条锯齿曲线。
HISTORY_ROOT = "reports/allure-history"
HISTORY_KEEP = 20  # 趋势图与每条用例的历史，只保留最近 20 次运行

# 报告归档：每次运行把 HTML 报告复制一份，便于事后回看"第 N 次"的现场。
# allure-html 每次 generate --clean 都会覆盖，不归档就只剩最新一次。
ARCHIVE_ROOT = "reports/archive"
ARCHIVE_KEEP_PASS = 20  # 通过的运行只留最近 20 份
ARCHIVE_KEEP_FAIL = 30  # 有 failed/broken 的运行留最近 30 份（防服务全挂时无限增长）

# 这四个文件都是"每跑一次追加一条"的数组，截断时必须同步处理，否则各图点数会不一致
TREND_FILES = (
    "history-trend.json",
    "duration-trend.json",
    "categories-trend.json",
    "retry-trend.json",
)

# 执行范围 -> 中文短标签（趋势图横轴、运行器名称里用）
SCOPE_LABELS = {
    "full": "全量",
    "smoke": "冒烟",
    "auth": "登录",
    "booking": "预订",
    "regression": "回归",
    "filtered": "筛选",
}

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


# ---- 执行范围 --------------------------------------------------------------
def detect_scope(session):
    """
    从 pytest 命令行推断本次执行范围

    - 没有 -m / -k：full
    - -m 命中已注册的标记：直接用标记名（smoke / booking / auth / regression）
    - 其他 -m 表达式或 -k：filtered

    报告的「环境」面板、运行器名称、历史目录都依赖这个值，
    所以只能有一处实现，避免三处各算一套导致对不上。
    """
    markexpr = (getattr(session.config.option, "markexpr", "") or "").strip()
    keyword = (getattr(session.config.option, "keyword", "") or "").strip()

    if not markexpr and not keyword:
        return "full"
    if markexpr in SCOPE_LABELS:
        return markexpr
    return "filtered"


def _scope_text(scope, collected):
    """趋势图/运行器上的范围描述，例如「全量40条」"""
    label = SCOPE_LABELS.get(scope, scope)
    return f"{label}{collected}条" if collected else label


# ---- 环境面板 + 失败分类 ----------------------------------------------------
def _repo_commit():
    """
    测试框架自身的 commit

    作用：同一台机器上不同代码版本跑出来的报告要能区分开——
    "这次红了是用例改坏了，还是被测服务改坏了"。
    取不到（没装 git / 不是仓库）就返回空串，不能让报告辅助本身失败。
    """
    try:
        result = subprocess.run(
            ["git", "-C", ROOT_DIR, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def write_allure_metadata(session, scope=None, results_dir=RESULTS_DIR):
    """
    往结果目录写两份元数据：

    1. environment.properties —— Allure 报告左侧「环境」面板的数据源，
       会显示被测地址、环境名、执行范围、Python / pytest 版本、框架 commit
    2. categories.json —— 失败分类规则，报告里的「分类」页靠它把失败归到
       「响应时间门禁超限 / 被测服务不可用 / 断言失败」

    时机：必须在 allure 的 --clean-alluredir 之后写（它会清空结果目录），
         所以放在会话结束时调用。

    :param session: pytest 会话对象
    :param scope: 执行范围；不传则现算
    :param results_dir: 结果目录（跟随实际生效的 --alluredir）
    :return: environment.properties 的生成路径
    """
    scope = scope or detect_scope(session)
    markexpr = (getattr(session.config.option, "markexpr", "") or "").strip()
    keyword = (getattr(session.config.option, "keyword", "") or "").strip()

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
        ("framework_commit", _repo_commit() or "unknown"),
        ("run_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]

    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, "environment.properties")
    with open(path, "w", encoding="utf-8") as f:
        for key, value in lines:
            f.write(f"{key}={value}\n")

    if os.path.exists(CATEGORIES_SRC):
        shutil.copyfile(CATEGORIES_SRC, os.path.join(results_dir, "categories.json"))

    return path


# ---- 历史（趋势）-----------------------------------------------------------
def history_dir(scope):
    """某个执行范围对应的历史目录"""
    return os.path.join(HISTORY_ROOT, scope)


def _read_json(path):
    """读 json，读不到或格式不对统一返回 None（报告辅助本身不该让用例失败）"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def sync_history_in(results_dir=RESULTS_DIR, scope="full"):
    """
    把上一轮的历史拷进结果目录（生成报告前调用）

    Allure 只从「输入目录」（--alluredir 指向的地方）读历史，不看输出目录，
    也不是"不删输出目录就会自动累积"。所以历史必须先落到结果目录里，
    再执行 generate --clean 才能接上。

    :return: True 表示拷了历史；False 表示还没有历史（首次运行）
    """
    src = history_dir(scope)
    if not os.path.isdir(src) or not os.listdir(src):
        return False

    dst = os.path.join(results_dir, "history")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return True


def _truncate_history(target_dir, keep=HISTORY_KEEP):
    """把趋势数组和每个用例的历史条目截断到最近 keep 条（原地改写）"""
    for name in TREND_FILES:
        path = os.path.join(target_dir, name)
        data = _read_json(path)
        if isinstance(data, list) and len(data) > keep:
            _write_json(path, data[-keep:])

    path = os.path.join(target_dir, "history.json")
    data = _read_json(path)
    if not isinstance(data, dict):
        return

    changed = False
    for entry in data.values():
        items = entry.get("items") if isinstance(entry, dict) else None
        if isinstance(items, list) and len(items) > keep:
            entry["items"] = items[-keep:]
            changed = True
    if changed:
        _write_json(path, data)


def sync_history_out(report_dir=REPORT_DIR, scope="full"):
    """
    把本次生成的历史存回仓库目录，并截断到最近 HISTORY_KEEP 次（生成后调用）

    存回的位置独立于报告目录，所以删掉 allure-html 不会把历史一起丢掉。

    :return: True 表示已保存
    """
    src = os.path.join(report_dir, "history")
    if not os.path.isdir(src):
        return False

    dst = history_dir(scope)
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        source = os.path.join(src, name)
        # 只拷文件：history 目录里都是 json，没有子目录
        if os.path.isfile(source):
            shutil.copyfile(source, os.path.join(dst, name))

    _truncate_history(dst)
    return True


# ---- 运行器 ----------------------------------------------------------------
def _build_order(results_dir):
    """
    buildOrder：第几次运行 = 历史里最大的序号 + 1

    不能用"历史条数 + 1"：历史只保留最近 20 条，跑到第 21 次时条数会一直
    卡在 20，序号就停在 21 不再增长，趋势图横轴会重复、归档目录会重名。
    """
    data = _read_json(os.path.join(results_dir, "history", "history-trend.json"))
    if not isinstance(data, list) or not data:
        return 1

    orders = []
    for entry in data:
        try:
            orders.append(int(entry.get("buildOrder")))
        except (AttributeError, TypeError, ValueError):
            continue
    return max(orders) + 1 if orders else 1


def _run_time_text(started_at):
    """运行开始时间，标签里精确到秒（批量跑时相邻两次可能只差 30 秒）"""
    moment = datetime.fromtimestamp(started_at) if started_at else datetime.now()
    return moment.strftime("%m-%d %H:%M:%S")


def write_executor(results_dir=RESULTS_DIR, scope="full", collected=0, started_at=None):
    """
    写 executor.json：报告的「运行器」面板 + 趋势图的横轴标签

    趋势图每个点靠 buildOrder 排序、靠 buildName 标注。缺这个文件时，
    历史条目里只有 data 没有名字，趋势图就是一串无名点——所以它和历史是一件事。

    本地标签带运行时间（精确到秒），因为批量跑时相邻两次可能只差几十秒；
    commit 不进标签（太长，环境面板的 framework_commit 里有）。
    CI 标签用 run number，链接直接能跳到Actions，不再重复时间。

    :param results_dir: 结果目录（跟随实际 --alluredir）
    :param scope: 执行范围
    :param collected: 本次收集到的用例数，用于「全量40条」这样的标签
    :param started_at: 本次会话开始时间（epoch 秒），用于标签上的时间
    :return: executor.json 的生成路径
    """
    scope_text = _scope_text(scope, collected)

    if os.getenv("GITHUB_ACTIONS") == "true":
        server = os.getenv("GITHUB_SERVER_URL", "")
        repo = os.getenv("GITHUB_REPOSITORY", "")
        run_id = os.getenv("GITHUB_RUN_ID", "")
        number = os.getenv("GITHUB_RUN_NUMBER", "")
        workflow = os.getenv("GITHUB_WORKFLOW", "CI")
        name = f"{workflow} #{number}" if number else workflow
        executor = {
            "name": "GitHub Actions",
            "type": "github",
            # CI 的 run number 天然单调递增，比本地推算更可靠
            "buildOrder": int(number) if number.isdigit() else _build_order(results_dir),
            "buildName": f"{name} · {scope_text}",
            "buildUrl": f"{server}/{repo}/actions/runs/{run_id}" if run_id else "",
            "reportName": name,
        }
    else:
        order = _build_order(results_dir)
        label = f"本地 第{order}次 · {scope_text} · {_run_time_text(started_at)}"
        executor = {
            "name": "本地运行",
            "type": "local",
            "buildOrder": order,
            "buildName": label,
            "reportName": label,
        }

    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, "executor.json")
    _write_json(path, executor)
    return path


def prepare_allure_inputs(session):
    """
    会话结束时的报告准备：历史 → 环境面板/分类 → 运行器

    顺序有依赖：先拷历史，write_executor 才能按"已经跑过几次"算出 buildOrder。

    :param session: pytest 会话对象
    """
    # 以实际生效的 --alluredir 为准：pytest.ini 里是默认值，命令行可能覆盖
    results_dir = getattr(session.config.option, "allure_report_dir", None) or RESULTS_DIR
    scope = detect_scope(session)

    if sync_history_in(results_dir, scope):
        logger.info(f"已接上历史趋势：{history_dir(scope)}")
    else:
        logger.info(f"暂无历史趋势（{scope} 首次运行）")

    write_allure_metadata(session, scope, results_dir)
    write_executor(results_dir, scope, session.testscollected,
                   started_at=getattr(session, "start_time", None))


# ---- 报告归档 --------------------------------------------------------------
def _report_status(report_dir):
    """
    读报告自己的 summary.json 判定这次运行是 PASS 还是 FAIL

    不在 pytest 侧数失败：session.testsfailed 分不清 failed/broken，
    而 summary.json 是报告实际渲染用的口径，两边一定一致。

    :return: "PASS" / "FAIL"；读不到 summary.json 时返回 None
    """
    data = _read_json(os.path.join(report_dir, "widgets", "summary.json"))
    if not isinstance(data, dict):
        return None

    stat = data.get("statistic") or {}
    bad = (stat.get("failed") or 0) + (stat.get("broken") or 0)
    return "FAIL" if bad else "PASS"


def _prune_archive(scope):
    """按规则清理旧归档：通过的留最近 N 份，失败的留最近 N 份"""
    base = os.path.join(ARCHIVE_ROOT, scope)
    if not os.path.isdir(base):
        return

    names = sorted(
        (name for name in os.listdir(base)
         if os.path.isdir(os.path.join(base, name))),
        # 按目录名里的序号（整数）排序，不依赖字符串补齐位数：
        # 跑到第 1000 次时 "1000_..." 按字符会排到 "999_..." 前面
        key=lambda name: int(name.split("_")[0]) if name.split("_")[0].isdigit() else 0,
    )

    for suffix, keep in (("_PASS", ARCHIVE_KEEP_PASS), ("_FAIL", ARCHIVE_KEEP_FAIL)):
        if keep <= 0:
            continue
        group = [name for name in names if name.endswith(suffix)]
        # 目录名里的序号是零填充的，字典序即运行顺序，最旧的排在最前
        for name in group[:-keep]:
            shutil.rmtree(os.path.join(base, name), ignore_errors=True)


def archive_report(results_dir=RESULTS_DIR, report_dir=REPORT_DIR, scope="full", started_at=None):
    """
    把本次生成的报告复制一份到 reports/archive/{scope}/，供事后回看

    目录名：{序号:03d}_{日期}_{时间}_{PASS|FAIL}
      - 序号零填充，字典序即时间序，清理时直接切片
      - FAIL 一眼可见，便于挑出有问题的运行

    :return: 归档目录路径；判定失败或复制出错时返回 None
    """
    status = _report_status(report_dir)
    if status is None:
        logger.warning("读不到报告的 summary.json，跳过归档")
        return None

    executor = _read_json(os.path.join(results_dir, "executor.json")) or {}
    try:
        order = int(executor.get("buildOrder"))
    except (TypeError, ValueError):
        order = 0

    moment = datetime.fromtimestamp(started_at) if started_at else datetime.now()
    name = f"{order:03d}_{moment.strftime('%Y-%m-%d_%H-%M-%S')}_{status}"
    dest = os.path.join(ARCHIVE_ROOT, scope, name)

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        shutil.rmtree(dest, ignore_errors=True)

    try:
        shutil.copytree(report_dir, dest)
    except OSError as e:
        logger.error(f"报告归档失败：{e}")
        return None

    _prune_archive(scope)
    logger.info(f"报告已归档：{dest}")
    return dest


# ---- 报告生成 --------------------------------------------------------------
def generate_local_report(results_dir=RESULTS_DIR, report_dir=REPORT_DIR, scope="full", started_at=None):
    """
    本地跑完测试后生成 Allure 报告、把历史存回仓库、归档报告、设中文、打开浏览器

    CI 里不要调用：workflow 会显式执行 allure generate，且没有浏览器可开。

    :param scope: 执行范围，决定历史与归档存进哪个子目录
    :param started_at: 会话开始时间（epoch 秒），用于归档目录名
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

    # 生成后把历史存回仓库目录，下一次运行才有趋势可接
    if sync_history_out(report_dir, scope):
        logger.info(f"历史趋势已保存：{history_dir(scope)}")
    else:
        logger.warning("报告里没有 history 目录，跳过历史保存")

    # 归档一份：allure-html 下次会被 --clean 覆盖，不归档就查不到"第 N 次"的现场
    archive_report(results_dir, report_dir, scope, started_at)

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
