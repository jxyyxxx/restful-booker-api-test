# Restful-Booker 接口自动化测试框架

基于 restful-booker 酒店预订系统的 pytest 接口自动化测试框架：分层架构 + YAML 数据驱动 + Allure 报告 + GitHub Actions 持续集成。

[![CI](https://github.com/jxyyxxx/restful-booker-api-test/actions/workflows/ci.yml/badge.svg)](https://github.com/jxyyxxx/restful-booker-api-test/actions/workflows/ci.yml)

- 仓库地址：<https://github.com/jxyyxxx/restful-booker-api-test>
- 在线 Allure 报告：<https://jxyyxxx.github.io/restful-booker-api-test/>

| 项目 | 说明 |
|------|------|
| 用例规模 | 40 条（登录 15 / 查询 9 / 创建 11 / 修改 2 / 删除 1 / 权限 1 / 探活 1） |
| 技术栈 | Python 3.11 / pytest / requests / PyYAML / Allure / GitHub Actions |
| 被测系统 | restful-booker（Node.js + Express + LokiJS 内存数据库，8 个接口） |
| 报告 | Allure（本地生成 + CI 自动发布到 GitHub Pages） |

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

### 3. 安装 Allure 命令行工具（生成 HTML 报告需要，需 Java 环境）

```cmd
npm install -g allure-commandline@2.30.0
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

### 5. 查看报告与日志

- Allure 结果：`reports/allure-results/`（由 `pytest.ini` 的 `addopts` 自动生成）
- HTML 报告：本地跑完由 `conftest.py` 的钩子自动 `allure generate` 并打开浏览器；也可手动 `allure open reports/allure-html`
- 明细日志：`logs/{环境}_{时间}.log`，记录每个请求的 URL、方法、请求体、状态码、响应体、耗时

**临时改被测地址**（不用改代码）：

```powershell
$env:BASE_URL = 'http://192.168.1.20:3001'; pytest -q    # PowerShell
set BASE_URL=http://192.168.1.20:3001 && pytest -q       # cmd
BASE_URL=http://192.168.1.20:3001 pytest -q              # bash
```

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

## 用例分层与标记

| 标记 | 打在哪 | 命中条数 | 命令 |
|------|--------|----------|------|
| `smoke` | 探活 + 主链路 6 条用例 | 6 | `pytest -m smoke` |
| `booking` | 5 个预订模块测试类（类级） | 24 | `pytest -m booking` |
| `auth` | 登录模块测试类（类级） | 15 | `pytest -m auth` |
| `regression` | 预留，暂未使用 | 0 | — |

**冒烟集 = `/ping` 探活 + 正向登录（token 格式）+ 查询列表 + PUT 全量修改 + PATCH 部分修改 + 删除**，跑一遍等于先确认服务在线，再走完「登录 → 创建 → 查询 → 修改 → 删除」主链路（创建由 `test_booking` fixture 间接触发），耗时约 0.4 秒。

> `/ping` 能排在最前，是 `conftest.py` 的 `pytest_collection_modifyitems` 把 health 模块提到收集结果最前；否则按文件名排序它会在最后，服务挂掉时先红的是一屏连接错误。

两个容易踩的点：

1. **冒烟标记只打在非参数化函数上**。参数化用例（登录 14 条、创建 11 条、查询详情 7 条）不能整体打 `smoke`，否则 14 条登录数据会全部变成冒烟，粒度就废了。
2. **`--strict-markers` 只管装饰器，不管命令行**。写 `@pytest.mark.smooke` 会直接报错；但 `pytest -m smooke` 拦不住，结果是 `40 deselected` + 退出码 5（"没收集到用例"）——CI 照样会红，只是提示不如前者清楚。

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 目录结构、分层职责、环境与接口、fixture、框架特性、依赖管理 |
| [docs/allure.md](docs/allure.md) | 报告里有什么（环境面板/scope/分类/严重级别/步骤）、默认中文、报告不更新怎么办 |
| [docs/ci.md](docs/ci.md) | 触发方式与分层、手动触发、执行步骤、关键约定、本地与 CI 差异 |
| [docs/pytest-config.md](docs/pytest-config.md) | `pytest.ini` 逐项说明 |

## 项目结构（顶层）

```
api/          接口方法层（与业务接口一一对应）
common/       工具层（HTTP 封装、断言、数据工厂、脱敏、日志、报告）
config/       配置层（环境、时延门限、Allure 分类规则）
data/         数据层（YAML，按模块分目录）
testcases/    用例层（health / auth / booking）
docs/         文档（架构、报告、CI、pytest 配置）
conftest.py   夹具与钩子
pytest.ini    pytest 配置
run.py        执行入口
```

完整目录树与每层职责见 [docs/architecture.md](docs/architecture.md)。
