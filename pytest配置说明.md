# pytest.ini 配置说明

pytest 运行时自动读取这个文件，控制测试的运行规则。本文档与 `pytest.ini` 逐项对应，改配置时请同步改这里。

---

## 配置项说明

### `disable_test_id_escaping_and_forfeit_all_rights_to_community_support = True`
禁用中文用例名的 Unicode 转义，让参数化用例的中文名字正常显示（不显示成 `\uXXXX`）。

---

### `python_files = test_*.py`
测试文件命名规则：只有以 `test_` 开头的 `.py` 文件才会被 pytest 当作测试文件收集。

---

### `python_classes = Test*`
测试类命名规则：只有以 `Test` 开头的类才会被收集。

---

### `python_functions = test_*`
测试函数命名规则：只有以 `test_` 开头的函数才会被当作测试用例执行。

---

### `markers`
自定义测试标记，用来给用例分类，运行时可以用 `-m` 筛选。
```bash
pytest -m smoke    # 只跑主链路冒烟集（6 条）
pytest -m booking  # 只跑预订模块（24 条）
pytest -m auth     # 只跑登录模块（15 条）
pytest -m "not smoke"   # 反向筛选：跳过冒烟集
```
当前定义的标记（都已实际打在用例上）：

| 标记 | 打在哪 | 命中条数 | 说明 |
|------|--------|----------|------|
| `smoke` | 探活 + 5 个非参数化主链路用例（函数级） | 6 | `/ping` 探活、正向登录、查询列表、PUT 修改、PATCH 修改、删除；创建由 fixture 间接触发 |
| `booking` | 5 个预订模块测试类（类级） | 24 | 查询 / 创建 / 修改 / 删除 / 未认证 |
| `auth` | `TestAuth` 测试类（类级） | 15 | 登录模块全部用例 |
| `regression` | 预留，暂未使用 | 0 | 需要"全量回归"语义时再用 |

> 为什么冒烟只打在非参数化用例上：参数化用例一个函数会展开成多条（如登录 14 条），
> 在函数上打 `smoke` 会让这 14 条全部进入冒烟集，粒度就失去了。
> 想精确到单条参数，需要在 YAML 里声明 marks 并让 DataLoader 透传（`pytest.param(..., marks=...)`），成本不划算。

---

### `addopts = -v --alluredir=reports/allure-results --clean-alluredir --strict-markers`
默认命令行参数，每次运行 `pytest` 自动带上，不用每次手动敲：
- `-v`：显示详细输出（每条用例的名字和结果）
- `--alluredir=reports/allure-results`：生成 Allure 结果文件（JSON 格式）到指定目录
- `--clean-alluredir`：运行前先清空旧的结果文件，避免历史数据干扰
- `--strict-markers`：使用未在 `markers` 里注册的标记时直接报错

**`--strict-markers` 的边界**（容易误解）：它只校验代码里 `@pytest.mark.xxx` 的装饰器名。
写 `@pytest.mark.smooke` 会立刻报错；但命令行 `pytest -m smooke` **不会**被它拦住——
那会得到 `40 deselected`、退出码 5（pytest 的"没收集到用例"专用码），CI 依然会判红，只是提示没那么直观。

> 注意：这里只生成 Allure 的 JSON 结果文件，HTML 报告由 conftest.py 里的 `pytest_sessionfinish` 钩子在测试结束后自动调用 `allure generate` 生成（CI 环境下该钩子会跳过，由 workflow 生成）。
>
> `reports/allure-results` 是 Allure 结果目录的**唯一真源**：本地钩子、CI 里的 `allure generate` 都读这个目录，
> 命令里不要再额外传 `--alluredir`，否则会出现两份结果、报告内容对不上。

---

### `testpaths = testcases`
测试用例搜索路径：pytest 只在 `testcases/` 目录下找测试用例，加快收集速度，避免误收集其他文件。

---

### `filterwarnings`
过滤警告信息，让输出更干净。当前配置是忽略所有 `DeprecationWarning`（弃用警告）。

---

### 日志配置（log_cli / log_level / log_format / log_date_format）
控制 pytest 运行时的日志输出，让日志在控制台实时显示：

- `log_cli = True`：开启控制台实时日志输出，用例运行过程中日志会实时打印到控制台
- `log_level = INFO`：控制台输出的日志级别，INFO 及以上级别的日志才会显示
- `log_format = [%(asctime)s] [%(levelname)s] %(message)s`：日志格式，包含时间、级别、消息
- `log_date_format = %Y-%m-%d %H:%M:%S`：日志里时间的显示格式

> 注意：这里配置的是 pytest 自带的日志输出，和项目里 `common/logger.py` 封装的日志工具是两套东西。pytest 的 log_cli 负责把用例里打日志实时显示到控制台，`common/logger.py` 负责把日志同时输出到控制台和文件。两者配合使用。

---

## 与 conftest.py 的配合关系

`conftest.py` 里有一个会话结束钩子 `pytest_sessionfinish`，负责在测试跑完后：

1. 调 `allure generate reports/allure-results -o reports/allure-html --clean` 生成 HTML 报告；
2. 调 `allure open reports/allure-html` 在浏览器打开。

**CI 环境下这个钩子会直接返回**（判断环境变量 `CI`），因为：

- GitHub Actions 里没有浏览器可开；
- workflow 已经显式执行了一次 `allure generate`，本地钩子再跑一遍属于重复劳动，还可能写坏同一份报告；
- `allure open` 会起一个常驻服务并继承 stdout，会把采集日志的管道挂住。

所以在 Jenkins、GitLab CI 等其他平台运行时，请显式设置 `CI=true`，让报告统一由流水线生成。
