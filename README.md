# Restful-Booker 接口自动化测试框架

基于 restful-booker 酒店预订系统的 pytest 接口自动化框架：分层架构 + YAML 数据驱动 + Allure 报告（趋势 / 归档 / 失败分类）+ GitHub Actions。

[![CI](https://github.com/jxyyxxx/restful-booker-api-test/actions/workflows/ci.yml/badge.svg)](https://github.com/jxyyxxx/restful-booker-api-test/actions/workflows/ci.yml)

- 仓库地址：<https://github.com/jxyyxxx/restful-booker-api-test>
- 在线 Allure 报告：<https://jxyyxxx.github.io/restful-booker-api-test/>

**40 条用例 · 8 个接口 · 全量执行 0.5~0.7 秒 · 冒烟 6 条约 0.4 秒 · 响应时间门禁 500ms**

## 快速开始

### 1. 启动被测服务（Node 18+）

```cmd
cd /d D:\restful-booker\restful-booker-main
npm install
npm install uuid@9.0.1
npm start
```

> `uuid` 必须降到 9.x：新版是纯 ESM，这个 CommonJS 服务直接 `require('uuid')`，不降版本起不来。
> 用 `npm start`（带 `SEED=true`，会灌 10 条种子数据）；直接 `node ./bin/www` 库是空的。

### 2. 装依赖并运行

```cmd
cd /d D:\restful-booker\restful-booker_测试框架
pip install -r requirements.lock     # 与 CI 完全一致；开发期可用 requirements.txt
pytest
```

跑完由 `conftest.py` 的会话结束钩子自动 `allure generate` 并在浏览器打开报告。常用命令：

| 命令 | 说明 |
|------|------|
| `pytest` | 全量 40 条 |
| `pytest -m smoke` | 冒烟 6 条，约 0.4 秒 |
| `pytest -m booking` / `-m auth` | 预订 24 条 / 登录 15 条 |
| `pytest "testcases/booking/test_create.py::TestBookingCreate" -vv` | 跑单个类，调试用 |
| `allure open reports/allure-html` | 手动打开报告（**别双击 index.html**） |

临时改被测地址不用改代码：`set BASE_URL=http://192.168.1.20:3001 && pytest`（bash 用 `BASE_URL=... pytest`）。

## 用例清单（40 条）

| 模块 | 文件 | 条数 | 标记 | 覆盖内容 |
|------|------|------|------|----------|
| 健康检查 | `health/test_ping.py` | 1 | `smoke` | `/ping` 返回 201（非 200），确认服务在线 |
| 登录 | `auth/test_login.py` | 15 | `auth` + `smoke`×1 | 正向登录、密码错误（空/简单）、用户名空/空格/不存在、两者均错、特殊字符、超长输入；token 格式 |
| 查询 | `booking/test_query.py` | 9 | `booking` + `smoke`×1 | 列表：自建数据后查列表，非空且每条含 `bookingid`；详情：自建数据查自己（200）+ 7 条非法 ID（404） |
| 创建 | `booking/test_create.py` | 11 | `booking` | 完整、缺可选字段、英文姓名、价格 0/超大、firstname 空、特殊字符；逐个缺必填字段（期望 500） |
| 修改 | `booking/test_update.py` | 2 | `booking` + `smoke`×2 | PUT 全量修改；PATCH 只改部分字段并验证未改字段不变 |
| 删除 | `booking/test_delete.py` | 1 | `booking` + `smoke`×1 | 删除返回 201，删除后查询返回 404 |
| 权限 | `booking/test_permission.py` | 1 | `booking` | 未认证修改返回 403，并清理造出的数据 |

> 设计原则：每条数据对应一个独立场景（等价类 / 边界值 / 异常输入），不用重复数据凑条数。

冒烟集 = `/ping` 探活 + 正向登录 + 查询列表 + PUT + PATCH + 删除，创建由 `test_booking` 夹具间接触发。
`smoke` 只打在非参数化函数上——参数化一个函数会展开成十几条，整体打标会让粒度失效。

## 踩过的坑

- **服务没起时先红一屏 `ConnectionError`**：`/ping` 按文件名排在最后，前面 39 条集体报连接失败。改成 `pytest_collection_modifyitems` 把 `testcases/health/` 提到收集最前。
- **趋势图永远只有一个点**：`history/` 放在结果目录里，被 `--clean-alluredir` 每次清空。挪到 `reports/allure-history/{scope}/`；`buildOrder` 取"历史里最大序号 + 1"而不是"条数 + 1"，否则第 21 次起横轴重复、归档重名。
- **数据泄漏 13 条/轮**：`GET /booking` 响应体越来越大，后续用例和压测都被污染。三条回收路径：夹具 `yield` 后置、创建用例 `finally`、会中断的用例兜底删除。
- **流水线自己变红**：上游 main 一提交，CI 就跑出无法复现的失败。锁 `SERVICE_COMMIT` + `requirements.lock`。
- **`--strict-markers` 只管装饰器**：`@pytest.mark.smooke` 立即报错，但 `pytest -m smooke` 拦不住——结果是 40 deselected + 退出码 5。
- **报告白屏**：`file://` 协议下数据加载失败，必须 `allure open`；另外 `reports/allure-results` 是唯一真源，命令行不要再额外传 `--alluredir`。

## 文档

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 三个关键设计（分层 / 数据回收 / 双门禁断言）及其代价 |
| [docs/allure.md](docs/allure.md) | 报告：环境面板、scope、趋势、归档、失败分类、默认中文 |
| [docs/ci.md](docs/ci.md) | 流水线：触发分层、锁版本、本地与 CI 差异 |

## 项目结构

```
api/          接口方法层（与业务接口一一对应）
common/       工具层（HTTP 封装、断言、数据工厂、脱敏、日志、报告）
config/       配置层（环境、时延门限、Allure 分类规则）
data/         数据层（YAML，按模块分目录）
testcases/    用例层（health / auth / booking）
conftest.py   夹具层（全局 fixture + 钩子）
pytest.ini    pytest 配置
run.py        执行入口
```

完整目录树与每层职责见 [docs/architecture.md](docs/architecture.md)。
