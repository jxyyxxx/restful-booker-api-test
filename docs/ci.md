# CI/CD 流水线

配置文件：`.github/workflows/ci.yml`

## 触发方式与执行广度（分层）

| 事件 | 跑什么 | 报告 scope |
|------|--------|-----------|
| `push`（任意分支） | 全量 40 条 | `full` |
| `pull_request` | 冒烟集 6 条（约 0.4 秒） | `smoke` |
| `schedule`（每天 00:00 UTC = 北京 08:00） | 全量 40 条 | `full` |
| `workflow_dispatch`（手动） | **下拉框自选**：`scope` = full / smoke，`python` = 3.11 / 3.13 | 跟随选择 |

PR 只跑冒烟是为了给提交快速反馈；`main` 的 push 与定时任务仍跑全量，保证线上报告是完整结果。

## 手动触发怎么用

仓库 → Actions → 左侧 CI → 右上「Run workflow（运行工作流程）」→ 选分支、`scope`（full=全量 / smoke=冒烟）、`python`（3.11 / 3.13）→ 运行。

- 选 `smoke` 时**不会覆盖线上报告**（线上链接只保留全量结果）；
- 非手动触发时 `inputs` 为空，工作流用 `inputs.python || '3.11'` 回落默认版本。

## 执行步骤

1. checkout → 安装 Python（默认 **3.11**，手动触发可切 **3.13**，带 pip 缓存）、Node.js 18
2. `pip install -r requirements.lock && pip check`（**锁定版本**安装，不使用 requirements.txt 的范围）、`npm install -g allure-commandline@2.30.0`
3. 克隆 restful-booker 并 `checkout` 到 **固定 commit**（`SERVICE_COMMIT`），再启动服务；打印被测服务 commit，60 秒内未响应则输出 `::error::` 并打印服务日志后失败
4. 按事件/输入选择测试范围：PR 与手动 smoke 跑 `pytest -m smoke -q`，其余跑 `pytest -q`（Allure 结果目录由 `pytest.ini` 的 `addopts` 决定，CI 不重复传参）
5. `allure generate` 生成 HTML 报告
6. `python -m common.reporting allure-report` 把报告默认语言设为中文
7. 上传 artifact：`reports/allure-results`、`allure-report`、`logs`、`service.log`（文件名带 Python 版本与 run_attempt，多次运行不覆盖）
8. 发布到 GitHub Pages（`gh-pages` 分支）

## 关键约定

| 约定 | 原因 |
|------|------|
| 测试步骤**不加** `continue-on-error` | 用例失败必须让流水线变红，否则"绿色"没有信息量 |
| 被测服务**锁定 commit** | 上游 main 随时会变，不锁的话流水线会"自己变红"，且失败原因无法复现 |
| 依赖走 `requirements.lock` | 上游发小版本不影响构建；`requirements.txt` 只做开发期的范围声明 |
| Python 版本**手动可选**（默认 3.11，可切 3.13） | 本地 3.13、CI 原先只有 3.11；需要跨版本验证时手动切一次即可，不必每次提交都跑两遍 |
| 报告归档用 `if: always()` | 用例失败时也要能拿到现场（结果、日志、服务输出） |
| 只发布**全量**报告，且仅限 `main` | PR、手动冒烟都不覆盖线上；避免链接里只剩 6 条用例的报告 |
| `permissions: contents: write` | 推送 `gh-pages` 需要写权限，新版仓库默认 token 只读 |
| `concurrency` 取消过期运行 | 同一分支连续提交时，旧流水线占资源且报告互相覆盖 |

## 本地与 CI 的行为差异

`conftest.py` 的 `pytest_sessionfinish` 检测到环境变量 `CI` 时直接返回，不做 `allure generate`、也不 `allure open`——CI 里报告由 workflow 显式生成一次，且没有浏览器可开。

所以在其他 CI（Jenkins 等）上运行本框架时，**记得设置 `CI=true`**，否则会重复生成报告，甚至挂住输出管道。

## 冒烟任务的报告在哪看

手动跑 `scope=smoke` 时报告不发布到 Pages，需要去这次运行的 **Artifacts（附件）** 下载 `test-reports-py{版本}-{attempt}`，解压后执行 `allure open allure-report` 查看。
