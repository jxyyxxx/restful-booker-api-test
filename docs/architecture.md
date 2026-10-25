# 架构与核心机制

本文说明框架的分层、目录、配置、夹具与三个关键设计的取舍。命令与用例清单见根目录 [README.md](../README.md)，报告细节见 [allure.md](allure.md)，流水线见 [ci.md](ci.md)。

## 目录结构

```
restful-booker_测试框架/
├── .github/workflows/
│   └── ci.yml                  # CI：拉起被测服务 → 跑用例 → 发布 Allure 报告
├── api/                        # 1️⃣ 接口方法层（与业务接口一一对应）
│   ├── auth_api.py             # 登录接口封装
│   └── booking_api.py          # 预订接口封装
├── common/                     # 2️⃣ 工具层（与业务无关的通用能力）
│   ├── http_client.py          # HTTP 统一封装（Session/超时/日志/步骤/脱敏）
│   ├── assert_utils.py         # 断言工具（8 个断言，均带 Allure 步骤）
│   ├── data_factory.py         # 测试数据工厂（随机造数、入住/离店日期）
│   ├── masking.py              # 日志脱敏（password/token → ***）
│   ├── data_loader.py          # YAML 数据加载（自动提取 case_name 作用例 ID）
│   ├── logger.py               # 日志（单例，控制台 + 文件双输出）
│   └── reporting.py            # Allure 报告（环境面板/失败分类/历史趋势/运行器/生成/默认中文）
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
│   ├── architecture.md         # 本文
│   ├── allure.md               # 报告说明
│   └── ci.md                   # 流水线说明
├── logs/                       # 6️⃣ 日志文件（{环境}_{时间}.log，已 gitignore）
├── reports/                    # 7️⃣ 报告目录（已 gitignore，CI 产物走 artifact）
│   ├── allure-results/         # Allure 结果文件（--clean-alluredir 每次重写）
│   ├── allure-history/         # 历史趋势（按 scope 分目录，保留最近 20 次）
│   ├── archive/                # 报告归档（序号+时间+状态，失败 30 份 / 通过 20 份）
│   └── allure-html/            # Allure HTML 报告（本地生成，每次覆盖）
├── conftest.py                 # 8️⃣ 夹具层（全局 fixture + 钩子注册）
├── pytest.ini                  # pytest 核心配置
├── run.py                      # 9️⃣ 执行入口
├── requirements.txt            # 开发期依赖范围（下界/上界）
├── requirements.lock           # 依赖锁：CI 用的精确版本
└── README.md
```

## 三个关键设计

### 1. 分层：依赖单向，改一处不动三处

依赖方向只有一条：**用例层 → 接口方法层 → 工具层 → 配置层**。

- 接口路径变了 → 只改 `api/`
- 断言规则变了 → 只改 `common/assert_utils.py`
- 测试数据变了 → 只改 YAML
- 换环境 / 调门限 → 只改环境变量，代码一行不动

**代价**：多一层跳转，读一条用例要跨 2~3 个文件。40 条规模下这笔成本是划算的；如果只有 5 条用例，这样分层属于过度设计——这一点在面试里要主动讲，否则会被当成"为了分层而分层"。

### 2. 测试数据：声明式造数 + 三条回收路径

正向用例**全部自己造数据**，不依赖服务的种子数据：查询列表、查询详情都先建一条再查。否则换一种启动方式（不设 `SEED=true`）就会出现"ID=1 查不到"的假失败。

回收有三条路径，对应三种失败方式：

| 路径 | 用在哪 | 为什么 |
|------|--------|--------|
| `test_booking` 夹具的 `yield` 后置 | 查询、修改类用例 | 前置/后置写在一处，用例里看不到清理代码 |
| 用例内 `finally` 删除 | 创建类用例（11 条中的 7 条正向） | 断言失败也要删，`finally` 是唯一保证 |
| 兜底再删一次 | 删除、未认证 403 | 这两条会中途切换登录态或提前删除，异常路径必须补一刀 |

不做回收的后果是可量化的：**每跑一轮泄漏 13 条预订**（7 条创建用例 + 6 条夹具/自建数据），`GET /booking` 的响应体越来越大，后续用例变慢，性能测试结果也会被污染（压测报告里记为"测试自污染"）。

> `test_booking` 依赖 `admin_login`（删除需要认证）。凡是自己清理数据的用例都必须**显式声明** `admin_login`，否则进用例时可能还没登录、`finally` 里删不掉——`test_permission` 里专门注释了这个坑。

### 3. 断言：功能与时延双门禁

接口测试通常只验"对不对"，这里补上"快不快"：`assert_response_time()` 给每个关键请求加了单次耗时上限，默认 **500ms**，可用 `RESPONSE_TIME_LIMIT` 覆盖。

- **覆盖范围**：`/ping`、`/auth`、查询列表/详情、创建、PUT、PATCH、删除、未认证 403；
- **失败信息**：带实际耗时与阈值，例如 `响应时间超限：GET /ping 耗时 7ms，超过阈值 0.1ms`；
- **阈值为什么取 500ms**：本地实测 2~20ms，留了一个数量级以上的余量——能拦住明显劣化（5ms → 800ms），又不会因 CI 机器抖动误报；
- **失败要能分类**：时延超限必须落进「响应时间门禁超限」，不能混进「断言失败」，否则值班的人会去改代码而不是查性能。`config/allure/categories.json` 里用负向断言保证三条规则互斥。

它和 JMeter 的分工：**这边拦回归劣化，那边测容量上限**，两者不重复。

## 环境信息

| 项目 | 信息 |
|------|------|
| 本地服务地址 | `http://localhost:3001` |
| 管理员账号 | `admin` / `password123` |
| 认证方式 | Cookie（`token=xxx`），由 `requests.Session` 自动管理 |
| 环境切换 | 环境变量 `ENV` 决定（白名单只有 `local`，写错直接 `ValueError`）；`BASE_URL` / `ADMIN_USER` / `ADMIN_PWD` 可覆盖默认值 |
| 响应时间门禁 | 默认 500ms，可用 `RESPONSE_TIME_LIMIT` 覆盖 |

> 本项目只跑本地服务（`npm start` 或 `docker compose up`），不维护在线环境。

## 核心接口

| 接口 | 方法 | 说明 | 是否需要认证 |
|------|------|------|--------------|
| `/ping` | GET | 健康检查（返回 **201**，不是 200） | 否 |
| `/auth` | POST | 登录获取 token（失败也返回 **200**，靠 `reason` 区分） | 否 |
| `/booking` | GET | 查询预订列表 | 否 |
| `/booking/{id}` | GET | 查询预订详情 | 否 |
| `/booking` | POST | 创建预订（缺必填字段返回 **500**） | 否 |
| `/booking/{id}` | PUT | 修改预订（全量） | ✅ 是 |
| `/booking/{id}` | PATCH | 修改预订（部分） | ✅ 是 |
| `/booking/{id}` | DELETE | 删除预订（成功返回 **201**） | ✅ 是 |

## 核心 fixture

| fixture | 作用域 | 说明 |
|---------|--------|------|
| `log_test_case` | function | 每个用例开始/结束打分隔日志（`autouse=True` 自动执行） |
| `admin_login` | session | 管理员登录一次，把 token 写入 `Session.cookies`，后续请求自动带认证 |
| `test_booking` | function | `yield` 实现前置造数 + 后置清理：用例前创建一条预订并返回 ID，用例结束后删除（用例失败也执行） |

## 其它实现细节

### 数据驱动与动态用例标题

测试数据按模块、按接口拆成独立 YAML，每条数据自带 `case_name`，作为 pytest 参数化 ID。

Allure 标题用 `allure.dynamic.title(f"...-{case_name}")` 在用例内部设置——**不能用 `@allure.title("{case_name}")`**：参数化传进来的是整个 dict，装饰器占位符取不到 dict 内部字段，报告里会原样显示成 `{case_name}`。

### 日志与脱敏

每次请求记录 URL、方法、请求体、状态码、响应体（截断 500 字符）、耗时；日志文件按 `{环境}_{时间}.log` 命名，方便按次排查。

请求体与响应体在写日志前统一脱敏（`password` / `token` / `authorization` / `cookie` → `***`），避免 `/auth` 的明文密码落进日志文件——这是日志工具里最容易漏的一环，脱敏放在 `common/masking.py` 单独一层，HTTP 封装只负责调用。

## 依赖管理

| 文件 | 用途 |
|------|------|
| `requirements.txt` | 开发期范围：下界=代码实际用到的最低版本，上界=下一个大版本 |
| `requirements.lock` | CI 用的精确版本（含传递依赖） |

**为什么两个都要**：范围声明表达"支持哪些版本"，锁文件保证"每次构建装到的是同一个版本"。上游发小版本不会把流水线打红，某次可复现的失败也不会被"重装一遍就绿了"掩盖。升级依赖时先改 `requirements.txt`，再用锁文件流程重新生成（步骤见 `requirements.lock` 头部注释），本地跑一遍全量再提交。
