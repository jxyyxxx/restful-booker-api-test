# pytest.ini 配置说明

pytest 运行时自动读取这个文件，控制测试的运行规则。

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
pytest -m smoke    # 只跑标记了 smoke 的用例
pytest -m booking  # 只跑标记了 booking 的用例
```
当前定义的标记：
- `smoke`：冒烟测试，核心主流程
- `regression`：回归测试，全量覆盖
- `auth`：登录模块
- `booking`：预订模块

---

### `addopts = -v --alluredir=reports/allure-results --clean-alluredir`
默认命令行参数，每次运行 `pytest` 自动带上，不用每次手动敲：
- `-v`：显示详细输出（每条用例的名字和结果）
- `--alluredir=reports/allure-results`：生成 Allure 结果文件（JSON 格式），存到指定目录
- `--clean-alluredir`：运行前先清空旧的结果文件，避免历史数据干扰

> 注意：这里只生成 Allure 的 JSON 结果文件，HTML 报告由 conftest.py 里的 `pytest_sessionfinish` 钩子在测试结束后自动调用 `allure generate` 生成。

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
