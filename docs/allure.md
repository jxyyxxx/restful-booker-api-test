# Allure 报告说明

报告由 `conftest.py` 的 `pytest_sessionfinish` 在会话结束时补齐元数据，本地与 CI 同样生效。生成/查看命令见根目录 [README.md](../README.md)。

## 报告里能看到什么

| 位置 | 数据来源 | 能看到什么 |
|------|----------|-----------|
| 用例步骤 | `common/http_client.py`、`common/assert_utils.py` 里的 `allure.step` | 点开一条用例，能看到「POST /auth → 断言：状态码 == 200 → 断言：字段 token 存在」这样的步骤链，失败时直接定位到哪一步 |
| 左侧「环境」面板 | `reports/allure-results/environment.properties` | 被测地址、环境名、Python / pytest 版本、操作系统，**以及本次执行范围** |
| 「分类」页 | `config/allure/categories.json`（跑测试时拷进结果目录，生成成 `categories.json`） | 失败自动归为「响应时间门禁超限」「被测服务不可用 / 连接异常」「断言失败（功能不符合预期）」；三条规则互斥（"断言失败"用负向断言排除了时延超限），不会一条失败同时进两个分类 |
| 「严重级别」视图 | 用例类上的 `@allure.severity` | 核心链路标 `CRITICAL`（`/ping` 探活、登录、创建），其余标 `NORMAL` |
| 概览 / 套件 | 用例的 feature / story / 动态标题 | 按「健康检查 / 登录认证 / 预订管理」分组，用例名带 `case_name` |

## 报告的默认语言

Allure 报告默认是英文，语言选择存在浏览器 `localStorage` 里，换个端口打开就要重新切一次。
本框架在生成报告后调用 `common/reporting.py` 往 `index.html` 注入一小段脚本，**打开即中文，无需手动切换**：

```bash
python -m common.reporting reports/allure-html   # 本地手动执行（conftest 已自动调用）
python -m common.reporting allure-report         # CI 里由 workflow 的同名步骤执行
python -m common.reporting <dir> --lang en       # 需要时切回英文
```

脚本是幂等的（重复执行不会重复注入），浏览器禁用 `localStorage` 时静默跳过、不影响报告打开。

## 报告里怎么区分「冒烟」和「全量」

不用手动标注，`scope` 字段是从 pytest 命令行自动推断的：

| 命令 | scope | markexpr | collected |
|------|-------|----------|-----------|
| `pytest` | `full` | `(none)` | 40 |
| `pytest -m smoke` | `smoke` | `smoke` | 6 |
| `pytest -m "not smoke"` | `filtered` | `not smoke` | 34 |

所以同一个报告链接，冒烟跑和全量跑在「环境」面板里一眼可辨：

```
env=local
base_url=http://localhost:3001
scope=smoke
markexpr=smoke
collected=6
response_time_limit_s=0.5
```

> CI 里 PR 跑冒烟、push 与定时跑全量，所以同一个链接上的 `scope` 会在 `smoke` 与 `full` 之间切换，
> 看报告前先瞄一眼环境面板就知道这份报告覆盖了多少条用例。

## 报告没更新怎么办

1. 先确认这次 CI 是否成功——只有 `main` + 全绿 + 全量才会发布；
2. 强刷（`Ctrl + Shift + R`）或用无痕窗口：Allure 是静态单页应用，`data/*.json` 会被缓存；GitHub Pages 还有几十秒的 CDN 传播；
3. 用数据文件判断新鲜度：打开 `widgets/summary.json`，看 `time.start` 是否更新。
