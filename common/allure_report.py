# ============================================================
# Allure 报告后处理：把默认语言固化为中文
#
# 原理：Allure 报告前端的语言选择保存在 localStorage 的
#      ALLURE_REPORT_SETTINGS.language 里，默认是 en（英文）。
#      这里往生成好的 index.html 注入一小段脚本，在 app.js 启动前
#      先写入 language=zh，于是任何人第一次打开报告看到的就是中文，
#      不需要在左下角手动切换。
#
# 用法：
#   python -m common.allure_report reports/allure-html      # 本地生成的报告
#   python -m common.allure_report allure-report            # CI 里生成的报告
#   python -m common.allure_report <dir> --lang en          # 需要时改回英文
# ============================================================

import argparse
import os

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

ANCHOR = '<script src="app.js"></script>'


def set_default_language(report_dir, lang="zh"):
    """
    往 Allure 报告的 index.html 注入"默认语言"脚本（幂等）

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

    if ANCHOR not in html:
        return False

    script = SCRIPT_TEMPLATE.replace("__LANG__", lang)
    html = html.replace(ANCHOR, "    " + script + "    " + ANCHOR, 1)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="把 Allure 报告的默认语言设为中文")
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
