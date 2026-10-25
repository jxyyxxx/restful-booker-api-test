# Allure 报告说明

报告由 `conftest.py` 的 `pytest_sessionfinish` 在会话结束时补齐元数据，本地与 CI 同样生效。生成/查看命令见根目录 [README.md](../README.md)。

## 报告里能看到什么

| 位置 | 数据来源 | 能看到什么 |
|------|----------|-----------|
| 用例步骤 | `common/http_client.py`、`common/assert_utils.py` 里的 `allure.step` | 点开一条用例，能看到「POST /auth → 断言：状态码 == 200 → 断言：字段 token 存在」这样的步骤链，失败时直接定位到哪一步 |
| 左侧「环境」面板 | `reports/allure-results/environment.properties` | 被测地址、环境名、Python / pytest 版本、操作系统、框架自身 commit，**以及本次执行范围** |
| 「趋势」图、「持续时长」图 | `reports/allure-history/{scope}/`（生成前拷进结果目录） | 每次运行的通过/失败数量、耗时曲线；按执行范围分开累积（全量一条线、冒烟一条线），点开单条用例还能看到「历史」标签页 |
| 顶部「运行器」 | `reports/allure-results/executor.json` | `本地 第3次 · 全量40条 · a1b2c3d` 或 `CI #123 · 全量40条`；CI 上可点进对应的 Actions run |
| 「分类」页 | `config/allure/categories.json`（跑测试时拷进结果目录，生成成 `categories.json`） | 失败自动归为「响应时间门禁超限」「被测服务不可用 / 连接异常」「断言失败（功能不符合预期）」；三条规则互斥（"断言失败"用负向断言排除了时延超限），不会一条失败同时进两个分类 |
| 「严重级别」视图 | 用例类上的 `@allure.severity` | 核心链路标 `CRITICAL`（`/ping` 探活、登录、创建），其余标 `NORMAL` |
| 概览 / 套件 | 用例的 feature / story / 动态标题 | 按「健康检查 / 登录认证 / 预订管理」分组，用例名带 `case_name` |

## 趋势与运行器

报告顶部那行 `本地 第3次 · 全量40条 · a1b2c3d` 和「趋势」图，靠两个输入文件：

| 文件 | 谁写 | 作用 |
|------|------|------|
| `reports/allure-history/{scope}/*.json` | `sync_history_out()`（生成后） | 上一次运行的历史，下一次生成前由 `sync_history_in()` 拷进结果目录 |
| `reports/allure-results/executor.json` | `write_executor()`（会话结束时） | 趋势图的横轴顺序（`buildOrder`）与标签（`buildName`） |

三个设计要点：

1. **历史放在结果目录之外**。`pytest.ini` 的 `--clean-alluredir` 每次会话开始都会清空结果目录，历史若放在里面，每跑一次就被清掉，趋势图永远只有一个点。
2. **按执行范围分目录**。`reports/allure-history/full/`、`/smoke/`、`/booking/`、`/auth/` 各存一份。全量 40 条和冒烟 6 条混在一条线上，趋势图会出现"用例丢了一半"的假象。
3. **只保留最近 20 次**（`HISTORY_KEEP`）。趋势数组和每个用例的历史同步截断，避免文件无限增长。

CI 侧：workflow 在跑测试前从 `gh-pages` 恢复上一份报告的 `history/` 到 `reports/allure-history/full/`，发布时再随报告一起推回去。因为线上只发布 main 上的全量结果，CI 那条趋势线天然是干净的。

想重置某条趋势线，直接删对应目录即可（不影响用例、不影响报告生成，只是从"第 1 次"重新开始）：

```bash
rm -rf reports/allure-history/full    # 只重置全量那条线
rm -rf reports/allure-history         # 全部重置
```

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
