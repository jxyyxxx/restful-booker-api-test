# Restful-Booker 接口自动化测试框架

基于 restful-booker 酒店预订系统的 pytest 接口自动化测试框架：分层架构 + YAML 数据驱动 + Allure 报告 + GitHub Actions 持续集成。

[![CI](https://github.com/jxyyxxx/restful-booker-api-test/actions/workflows/ci.yml/badge.svg)](https://github.com/jxyyxxx/restful-booker-api-test/actions/workflows/ci.yml)

- 仓库地址：<https://github.com/jxyyxxx/restful-booker-api-test>
- 在线 Allure 报告：<https://jxyyxxx.github.io/restful-booker-api-test/>

| 项目 | 说明 |
|------|------|
| 用例规模 | 40 条（参数化执行，覆盖登录 14 + 创建 11 + 查询 8 + 独立用例 7） |
| 技术栈 | Python 3.11 / pytest / requests / PyYAML / Allure / GitHub Actions |
| 被测系统 | restful-booker（Node.js + Express + LokiJS 内存数据库，8 个接口） |
| 报告 | Allure（本地生成 + CI 自动发布到 GitHub Pages） |

---

## 目录结构

```
restful-booker_测试框架/
├── .github/workflows/
│   └── ci.yml                  # CI 流水线：拉起被测服务 → 跑用例 → 发布 Allure 报告
├── api/                        # 1️⃣ 接口方法层（与业务接口一一对应）
│   ├── auth_api.py             # 登录接口封装
│   └── booking_api.py          # 预订接口封装
├── common/                     # 2️⃣ 工具层（与业务无关的通用能力）
│   ├── http_client.py          # HTTP 统一封装（Session/超时/日志/步骤/脱敏）
│   ├── assert_utils.py         # 断言工具（8 个断言，均带 Allure 步骤）
│   ├── data_factory.py         # 测试数据工厂（随机造数、入住/离店日期）
│   ├── masking.py              # 日志脱敏（password/token → ***）
│   ├── data_loader.py          # YAML 数据加载（自动提取 case_name 作用例 ID）
│   ├── logger.py               # 日志（单例，控制台+文件双输出）
│   └── reporting.py            # Allure 报告（环境面板/失败分类/生成/默认中文）
├── config/                     # 3️⃣ 配置层
│   ├── settings.py             # 环境、地址、账号、超时、时延门限、日志配置
│   └── allure/
│       └── categories.json     # 失败分类规则（跑测试时拷进结果目录）
├── data/                       # 4️⃣ 数据层（YAML，按模块分目录）
│   ├── auth/login.yaml         # 登录 14 条
│   └── booking/
│       ├── create.yaml         # 创建 11 条
│       └── query.yaml          # 查询 7 条（均为不存在的 ID）
├── testcases/                  # 5️⃣ 用例层（按模块分目录）
│   ├── health/
│   │   └── test_ping.py        # 健康检查 1 条（/ping，冒烟集第一条）
│   ├── auth/
│   │   └── test_login.py       # 登录 15 条（14 参数化 + 1 条 token 格式）
│   └── booking/
│       ├── test_query.py       # 查询 9 条（列表 1 + 自建详情 1 + 不存在 ID 7）
│       ├── test_create.py      # 创建 11 条
│       ├── test_update.py      # 修改 2 条（PUT + PATCH）
│       ├── test_delete.py      # 删除 1 条
│       └── test_permission.py  # 未认证 403 1 条
├── docs/
│   └── pytest-config.md        # pytest.ini 逐项说明
├── logs/                       # 6️⃣ 日志文件（按 {环境}_{时间}.log 命名，已 gitignore）
├── reports/                    # 7️⃣ 报告目录（已 gitignore，CI 产物走 artifact）
│   ├── allure-results/         # Allure 结果文件（JSON）
│   └── allure-html/            # Allure HTML 报告（本地生成）
├── conftest.py                 # 8️⃣ 夹具层（全局 fixture + 会话结束钩子）
├── pytest.ini                  # pytest 核心配置
├── run.py                      # 9️⃣ 执行入口（封装配置好的 pytest 命令）
├── requirements.txt            # 开发期依赖范围（下界/上界）
├── requirements.lock           # 依赖锁：CI 用的精确版本
└── README.md
```

---

## 环境信息

| 项目 | 信息 |
|------|------|
| 本地服务地址 | `http://localhost:3001` |
| 管理员账号 | `admin` / `password123` |
| 认证方式 | Cookie（`token=xxx`），由 `requests.Session` 自动管理 |
| 环境切换 | 环境变量 `ENV` 决定（当前白名单只有 `local`，写错会直接 `ValueError`）；`BASE_URL` / `ADMIN_USER` / `ADMIN_PWD` 可覆盖默认值，改环境不用改代码 |

> 本项目只跑本地服务（`npm start` 或 `docker compose up`），不再维护在线环境。

## 核心接口

| 接口 | 方法 | 说明 | 是否需要认证 |
|------|------|------|--------------|
| `/ping` | GET | 健康检查（返回 **201**，不是 200；已覆盖用例） | 否 |
| `/auth` | POST | 登录获取 token | 否 |
| `/booking` | GET | 查询预订列表 | 否 |
| `/booking/{id}` | GET | 查询预订详情 | 否 |
| `/booking` | POST | 创建预订 | 否 |
| `/booking/{id}` | PUT | 修改预订（全量） | ✅ 是 |
| `/booking/{id}` | PATCH | 修改预订（部分） | ✅ 是 |
| `/booking/{id}` | DELETE | 删除预订 | ✅ 是 |

---

## 快速开始

### 1. 启动 restful-booker 服务

```cmd
cd /d D:\restful-booker\restful-booker-main
npm install
npm install uuid@9.0.1
npm start
```

> `uuid@9.0.1` 是必须的：新版 uuid 是纯 ESM，而这个 CommonJS 服务直接 `require('uuid')`，不降版本会启动失败。

### 2. 安装测试依赖

```cmd
pip install -r requirements.txt          # 本地开发：范围安装（下界/上界）
pip install -r requirements.lock         # 想和 CI 完全一致：精确版本
```

> 版本范围写在 `requirements.txt` 里：下界是代码实际用到的最低版本，上界是下一个大版本——既避免上游破坏性变更打红，又不限制补丁升级。
> `requirements.lock` 是干净环境解析出的精确版本，CI 装的是它；升级依赖时先改 `requirements.txt`，再用锁文件流程重新生成
> （步骤见 `requirements.lock` 头部注释），本地跑一遍全量再提交。

### 3. 安装 Allure 命令行工具（生成 HTML 报告需要，需 Java 环境）

```cmd
npm install -g allure-commandline
allure --version
```

### 4. 运行测试

```cmd
python run.py                 # 入口文件，等价于 pytest
pytest                        # 全量，40 条
pytest -m smoke               # 冒烟集，6 条（探活 + 主链路，0.4 秒）
pytest -m booking             # 预订模块，24 条
pytest -m auth                # 登录模块，15 条
pytest testcases/booking/     # 按目录跑
pytest -q                     # 安静模式
```

**临时改被测地址**（比如指向另一台机器上的实例，不用改代码）：

```powershell
# PowerShell
$env:BASE_URL = 'http://192.168.1.20:3001'; pytest -q
# cmd
set BASE_URL=http://192.168.1.20:3001 && pytest -q
# bash
BASE_URL=http://192.168.1.20:3001 pytest -q
```

### 5. 查看报告与日志

- Allure 结果：`reports/allure-results/`（由 `pytest.ini` 的 `addopts` 自动生成）
- HTML 报告：本地跑完由 `conftest.py` 的 `pytest_sessionfinish` 钩子自动 `allure generate` 并打开浏览器
- 明细日志：`logs/{环境}_{时间}.log`，记录每个请求的 URL、方法、请求体、状态码、响应体、耗时

---

## 核心 fixture 说明

| fixture | 作用域 | 说明 |
|---------|--------|------|
| `log_test_case` | function | 每个用例开始/结束打分隔日志（`autouse=True` 自动执行） |
| `admin_login` | session | 管理员登录一次，把 token 写入 `Session.cookies`，后续请求自动带认证 |
| `test_booking` | function | 用 `yield` 实现前置造数 + 后置清理：用例前创建一条预订并返回 ID，用例结束后删除（用例失败也执行） |

**fixture 依赖关系**：`test_booking` 依赖 `admin_login`（删除接口需要认证）。凡是要清理数据的用例，都必须显式声明 `admin_login`，否则进用例时可能还没登录、`finally` 里删不掉，导致数据泄漏。

---

## 框架特性

### 1. 接口方法层封装
用例层不直接调 `http.get/post`，而是调 `booking_api.create_booking()` 这类业务方法；接口路径或参数变化时只改 `api/` 一个文件。

### 2. YAML 数据驱动 + 动态用例标题
测试数据按模块、按接口拆成独立 YAML，每条数据自带 `case_name`，作为 pytest 参数化 ID。
Allure 标题用 `allure.dynamic.title(f"...-{case_name}")` 在用例内部设置——**不能用 `@allure.title("{case_name}")`**，因为参数化传进来的是整个 dict，装饰器占位符取不到 dict 内部字段，报告里会原样显示成 `{case_name}`。

### 3. 断言工具类
`AssertUtils` 统一状态码、字段存在、字段值、列表类型、组合断言（如 `assert_create_booking_success`）等，报错信息带实际值。

### 4. 日志系统
每次请求记录 URL、方法、请求体、状态码、响应体（截断 500 字符）、耗时；日志文件按环境+时间命名，方便按次排查。
请求体与响应体在写日志前会做**脱敏**（`password` / `token` / `authorization` / `cookie` → `***`），避免 `/auth` 的明文密码落进日志文件。

### 5. 测试数据自动回收
三条回收路径：

- `test_booking` fixture 的 `yield` 后置清理（查询详情、修改类用例）；
- 创建类用例在 `finally` 里删除自己创建的预订；
- 会失败中断的用例（如删除、未认证 403）在 `finally` 里做一次**兜底删除**，避免用例中途失败留下脏数据。

不回收的后果很具体：每跑一轮就往系统里堆 9 条左右的预订，`GET /booking` 的响应体越来越大，后续用例和性能测试都会被污染（这一点在性能测试报告里被单独记为"测试自污染"）。

> 正向用例全部**自己造数据**（列表、详情都先建一条再查），不依赖服务启动时的种子数据——
> 否则换一种启动方式（不设 `SEED=true`）就会出现"ID=1 查不到"的假失败。

### 6. 用例按功能细分
一个测试文件只测一个功能，职责单一，好找好改。

### 7. 响应时间门禁
`AssertUtils.assert_response_time()` 给关键接口加了单次耗时上限：默认 500ms，可用环境变量 `RESPONSE_TIME_LIMIT` 覆盖。

- **覆盖范围**：`/ping`、`/auth`、查询列表与详情、创建、PUT、PATCH、删除、未认证 403；
- **失败信息**：带实际耗时与阈值，例如 `响应时间超限：GET /ping 耗时 7ms，超过阈值 0.1ms`；
- **阈值为什么取 500ms**：本地实测 2~20ms，留了一个数量级以上的余量——既能拦住明显劣化（比如某次改动让接口从 5ms 涨到 800ms），又不会因为 CI 机器抖动误报。

它让功能用例同时具备"对不对"和"快不快"两个维度，与 JMeter 的性能测试形成互补：这边拦**回归劣化**，那边测**容量上限**。

---

## 用例清单与规模（共 40 条）

| 模块 | 文件 | 条数 | 标记 | 覆盖内容 |
|------|------|------|------|----------|
| 健康检查 | `health/test_ping.py` | 1 | `smoke` | `/ping` 返回 201（非 200），确认服务在线，同时校验响应时间门禁 |
| 登录 | `auth/test_login.py` | 15 | `auth` + `smoke`×1 | 正向登录、密码错误（含空/简单密码）、用户名空/空格/不存在、用户名密码均错、特殊字符、超长输入；token 格式校验 |
| 查询 | `booking/test_query.py` | 9 | `booking` + `smoke`×1 | 列表：自建数据后查列表，非空且每条含 `bookingid`；详情：自建数据查自己（200）+ 7 条不存在/非法 ID（404：0、负数、超大值） |
| 创建 | `booking/test_create.py` | 11 | `booking` | 完整数据、缺可选字段、英文姓名、价格 0/超大值、firstname 空、特殊字符；逐个缺必填字段（期望 500） |
| 修改 | `booking/test_update.py` | 2 | `booking` + `smoke`×2 | PUT 全量修改；PATCH 只改部分字段并验证未改字段不变 |
| 删除 | `booking/test_delete.py` | 1 | `booking` + `smoke`×1 | 删除返回 201，删除后查询返回 404 |
| 权限 | `booking/test_permission.py` | 1 | `booking` | 未认证修改返回 403，并清理造出的数据 |

> 设计原则：每条数据对应一个独立场景（等价类 / 边界值 / 异常输入），不用重复数据凑条数。

---

## 用例分层与标记

`pytest.ini` 注册了四个标记，并且都已实际打在用例上（不是"声明了但没人用"）：

| 标记 | 打在哪 | 命中条数 | 命令 |
|------|--------|----------|------|
| `smoke` | 探活 + 主链路 6 条用例 | 6 | `pytest -m smoke` |
| `booking` | 5 个预订模块测试类（类级） | 24 | `pytest -m booking` |
| `auth` | 登录模块测试类（类级） | 15 | `pytest -m auth` |
| `regression` | 预留，暂未使用 | 0 | — |

**冒烟集 = `/ping` 探活 + 正向登录（token 格式）+ 查询列表 + PUT 全量修改 + PATCH 部分修改 + 删除**，跑一遍等于先确认服务在线，再走完「登录 → 创建 → 查询 → 修改 → 删除」主链路（创建由 `test_booking` fixture 间接触发），耗时约 0.4 秒。

> `/ping` 之所以能排在最前面，是因为 `conftest.py` 里的 `pytest_collection_modifyitems` 把健康检查模块提到收集结果的最前；
> 否则按文件名排序它会排在最后，服务挂掉时先红的就是几十条连接失败。

两个容易踩的点：

1. **冒烟标记只打在非参数化函数上**。参数化用例（登录 14 条、创建 11 条、查询详情 8 条）不能整体打 `smoke`，否则 14 条登录数据会全部变成冒烟，粒度就废了。想精确到某一条参数，得在数据和标记之间打通（如 `pytest.param(..., marks=...)`），成本不划算，所以用"圈定非参数化主链路"的方式。
2. **`--strict-markers` 只管装饰器，不管命令行**。写 `@pytest.mark.smooke` 会直接报错；但 `pytest -m smooke` 不会被拦住，结果是 `40 deselected` + 退出码 5（"没收集到用例"）——CI 照样会红，只是提示不如前者清楚。

当前 CI 仍然跑全量：40 条只要 0.7 秒，分层省不出时间。标记是为了以后用例变多、需要"push 跑冒烟、定时跑全量"时准备好的。

---

## Allure 报告里能看到什么

报告的可读性靠四块元数据，由 `conftest.py` 在会话结束时写入（本地与 CI 同样生效）：

| 位置 | 数据来源 | 能看到什么 |
|------|----------|-----------|
| 用例步骤 | `http_client.py`、`assert_utils.py` 里的 `allure.step` | 点开一条用例，能看到「POST /auth → 断言：状态码 == 200 → 断言：字段 token 存在」这样的步骤链，失败时直接定位到哪一步 |
| 左侧「环境」面板 | `reports/allure-results/environment.properties` | 被测地址、环境名、Python / pytest 版本、操作系统，**以及本次执行范围** |
| 「分类」页 | `config/allure/categories.json`（跑测试时拷进结果目录，生成成 `categories.json`） | 失败自动归为「响应时间门禁超限」「被测服务不可用 / 连接异常」「断言失败（功能不符合预期）」；三条规则互斥（"断言失败"用负向断言排除了时延超限），不会一条失败同时进两个分类 |
| 「严重级别」视图 | 用例类上的 `@allure.severity` | 核心链路标 `CRITICAL`（`/ping` 探活、登录、创建），其余标 `NORMAL` |
| 概览 / 套件 | 用例的 feature / story / 动态标题 | 按「健康检查 / 登录认证 / 预订管理」分组，用例名带 `case_name` |

### 报告的默认语言

Allure 报告默认是英文，语言选择存在浏览器 `localStorage` 里，换个端口打开就要重新切一次。
本框架在生成报告后调用 `common/reporting.py` 往 `index.html` 注入一小段脚本，
**打开即中文，无需手动切换**：

```bash
python -m common.reporting reports/allure-html   # 本地手动执行（conftest 已自动调用）
python -m common.reporting allure-report         # CI 里由 workflow 的同名步骤执行
python -m common.reporting <dir> --lang en       # 需要时切回英文
```

脚本是幂等的（重复执行不会重复注入），浏览器禁用 `localStorage` 时静默跳过、不影响报告打开。

### 报告里怎么区分「冒烟」和「全量」

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

> 需要注意：CI 里 PR 跑冒烟、push 与定时跑全量，所以同一个链接上的 `scope` 会在 `smoke` 与 `full` 之间切换，
> 看报告前先瞄一眼环境面板就知道这份报告覆盖了多少条用例。

---

## CI/CD 流水线

`.github/workflows/ci.yml`

**触发方式与执行广度（分层）**：

| 事件 | 跑什么 | 报告 scope |
|------|--------|-----------|
| `push`（任意分支） | 全量 40 条 | `full` |
| `pull_request` | 冒烟集 6 条（约 0.4 秒） | `smoke` |
| `schedule`（每天 00:00 UTC = 北京 08:00） | 全量 40 条 | `full` |
| `workflow_dispatch`（手动） | **下拉框自选**：`scope` = full / smoke，`python` = 3.11 / 3.13 | 跟随选择 |

PR 只跑冒烟是为了给提交快速反馈；`main` 的 push 与定时任务仍跑全量，保证线上报告是完整结果。

**手动触发怎么用**：仓库 → Actions → 左侧 CI → 右上「Run workflow（运行工作流程）」→ 选分支、`scope`（full=全量 / smoke=冒烟）、`python`（3.11 / 3.13）→ 运行。选 smoke 时不覆盖线上报告（见下方约定）。

**执行步骤**：

1. checkout → 安装 Python（默认 **3.11**，手动触发可切 **3.13**，带 pip 缓存）、Node.js 18
2. `pip install -r requirements.lock && pip check`（**锁定版本**安装，不使用 requirements.txt 的范围）、`npm install -g allure-commandline@2.30.0`
3. 克隆 restful-booker 并 `checkout` 到 **固定 commit**（`SERVICE_COMMIT`），再启动服务；打印被测服务 commit，60 秒内未响应则输出 `::error::` 并打印服务日志后失败
4. 按事件/输入选择测试范围：PR 与手动 smoke 跑 `pytest -m smoke -q`，其余跑 `pytest -q`（Allure 结果目录由 `pytest.ini` 的 `addopts` 决定，CI 不重复传参）
5. `allure generate` 生成 HTML 报告
6. `python -m common.reporting allure-report` 把报告默认语言设为中文
7. 上传 artifact：`reports/allure-results`、`allure-report`、`logs`、`service.log`（文件名带 Python 版本与 run_attempt，多次运行不覆盖）
8. 发布到 GitHub Pages（`gh-pages` 分支）

**关键约定**：

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

**本地与 CI 的行为差异**：`conftest.py` 的 `pytest_sessionfinish` 检测到环境变量 `CI` 时直接返回，不做 `allure generate`、也不 `allure open`——CI 里报告由 workflow 显式生成一次，且没有浏览器可开。所以在其他 CI（Jenkins 等）上运行本框架时，记得设置 `CI=true`，否则会重复生成报告甚至挂住输出管道。
