# CI/CD 流水线

配置文件：`.github/workflows/ci.yml`

## 触发与执行广度

| 事件 | 跑什么 | 报告 scope |
|------|--------|-----------|
| `push`（任意分支） | 全量 40 条 | `full` |
| `pull_request` | 冒烟集 6 条（约 0.4 秒） | `smoke` |
| `schedule`（每天 00:00 UTC = 北京 08:00） | 全量 40 条 | `full` |
| `workflow_dispatch`（手动） | 下拉框自选：`scope` = full / smoke，`python` = 3.11 / 3.13 | 跟随选择 |

PR 只跑冒烟是为了给提交快速反馈；`main` 的 push 与定时任务仍跑全量，保证线上报告是完整结果。

## 手动触发

仓库 → Actions → 左侧 CI → 右上「Run workflow」→ 选分支、`scope`、`python` → 运行。

- 选 `smoke` 时**不会覆盖线上报告**（线上链接只保留全量结果），报告要去这次运行的 **Artifacts** 下载 `test-reports-py{版本}-{attempt}`，解压后 `allure open allure-report` 查看；
- 非手动触发时 `inputs` 为空，工作流用 `inputs.python || '3.11'` 回落默认版本。

## 执行链

`checkout` → 从 `gh-pages` 恢复 `history/` 到 `reports/allure-history/full/` → 装 Python（默认 3.11）/ Node 18 → `pip install -r requirements.lock` + Allure CLI → 克隆 restful-booker 并 `checkout` 到固定 commit、启动服务（60 秒内不响应则打印服务日志并失败）→ 按事件选范围跑用例 → `allure generate` → 设报告默认中文 → 上传 artifact → 发布 `gh-pages`。

## 关键约定

| 约定 | 原因 |
|------|------|
| 测试步骤**不加** `continue-on-error` | 用例失败必须让流水线变红，否则"绿色"没有信息量 |
| 被测服务**锁定 commit**（`SERVICE_COMMIT`） | 上游 main 随时会变，不锁的话流水线会"自己变红"，且失败无法复现 |
| 依赖走 `requirements.lock` | 上游发小版本不影响构建；`requirements.txt` 只做开发期范围声明 |
| 只发布**全量**、且仅限 `main` | PR 与手动冒烟不覆盖线上，避免链接里只剩 6 条用例 |
| 发布时 `keep_files: true` | 某次生成失败导致没有 `history/` 时，保留旧文件，趋势不被清零 |
| `permissions: contents: write` + `concurrency` | 推 `gh-pages` 需要写权限（新仓库默认只读）；连续提交时取消旧流水线 |

## 本地与 CI 的差异

`conftest.py` 的 `pytest_sessionfinish` 检测到环境变量 `CI` 时直接返回，不做 `allure generate`、也不 `allure open`——CI 里报告由 workflow 显式生成一次，且没有浏览器可开。

所以在 Jenkins、GitLab CI 等其他平台运行本框架时，**记得设置 `CI=true`**，否则会重复生成报告，甚至挂住采集日志的管道。
