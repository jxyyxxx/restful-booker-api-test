# Restful-Booker 接口自动化测试框架

基于 restful-booker 酒店预订系统的 pytest 接口自动化测试框架，采用企业级标准分层架构。

## 目录结构

```
restful-booker_测试框架/
├── config/                     # 1️⃣ 配置层
│   └── settings.py             # 环境配置、全局常量
├── common/                     # 2️⃣ 工具层
│   ├── http_client.py          # HTTP 请求统一封装（Session自动管理Cookie）
│   ├── utils.py                # 通用工具（随机数据生成等）
│   ├── assert_utils.py         # 断言工具类（统一断言，减少重复）
│   ├── logger.py               # 日志工具类（控制台+文件双输出）
│   ├── data_loader.py          # YAML数据加载工具类
│   └── api/                    # 3️⃣ 接口方法层
│       ├── auth_api.py         # 登录接口封装
│       └── booking_api.py      # 预订接口封装
├── data/                       # 4️⃣ 数据层（YAML格式，按模块分目录，每个接口一个文件）
│   └── yaml/                   # YAML测试数据文件
│       ├── auth/               # 登录模块数据
│       │   └── login_data.yaml
│       └── booking/            # 预订模块数据
│           ├── create_data.yaml    # 创建预订
│           └── query_data.yaml     # 查询预订
├── testcases/                  # 5️⃣ 用例层（按功能细分）
│   ├── test_auth.py            # 登录模块测试
│   └── booking/
│       ├── test_booking_query.py    # 查询预订（列表+详情）
│       ├── test_booking_create.py   # 创建预订
│       ├── test_booking_update.py   # 修改预订（PUT+PATCH）
│       ├── test_booking_delete.py   # 删除预订
│       └── test_booking_auth.py     # 未认证权限测试
├── logs/                       # 6️⃣ 日志文件（按时间命名）
├── reports/                    # 7️⃣ 报告目录
│   ├── allure-results/         # Allure 结果文件（JSON）
│   └── allure-html/            # Allure HTML 报告
├── conftest.py                 # 8️⃣ 夹具层（全局 fixture）
├── pytest.ini                  # pytest 核心配置文件
├── run.py                      # 9️⃣ 执行入口
├── pytest配置说明.md            # pytest.ini 详细说明
└── README.md                   # 说明文档
```

## 环境信息

| 项目 | 信息 |
|------|------|
| 服务地址 | `http://localhost:3001` |
| 管理员账号 | `admin` |
| 管理员密码 | `password123` |
| 认证方式 | Cookie（token=xxx），Session 自动管理 |

## 核心接口

| 接口 | 方法 | 说明 | 是否需要认证 |
|------|------|------|--------------|
| `/auth` | POST | 登录获取 token | 否 |
| `/booking` | GET | 查询预订列表 | 否 |
| `/booking/{id}` | GET | 查询预订详情 | 否 |
| `/booking` | POST | 创建预订 | 否 |
| `/booking/{id}` | PUT | 修改预订（全量） | ✅ 是 |
| `/booking/{id}` | PATCH | 修改预订（部分） | ✅ 是 |
| `/booking/{id}` | DELETE | 删除预订 | ✅ 是 |

## 快速开始

### 1. 启动 restful-booker 服务
```cmd
cd /d D:\restful-booker\restful-booker-main
npm start
```

### 2. 安装测试依赖
```cmd
pip install pytest requests allure-pytest pyyaml
```

### 3. 安装 Allure 命令行工具（生成报告需要）
1. 下载 allure-commandline（需要 Java 环境）
2. 解压并配置环境变量
3. 验证：`allure --version`

### 4. 运行测试
```cmd
# 方式1：直接运行入口文件（自动生成 Allure 结果）
python run.py

# 方式2：命令行执行所有用例
pytest

# 方式3：只执行登录模块
pytest testcases/test_auth.py

# 方式4：只执行预订模块
pytest testcases/booking/
```

### 5. 生成并查看 Allure 报告
```cmd
# 生成 HTML 报告
allure generate reports/allure-results -o reports/allure-html --clean

# 打开报告
allure open reports/allure-html
```

### 6. 查看日志
每次运行自动在 `logs/` 目录下生成按时间命名的日志文件，记录每个请求的详细信息。

## 核心 fixture 说明

| fixture | 作用域 | 说明 |
|---------|--------|------|
| `check_env_health` | session | 环境健康检查，自动执行 |
| `log_test_case` | function | 自动记录每个用例的开始和结束日志 |
| `admin_login` | session | 全局登录，token 自动存入 Cookie |
| `test_booking` | function | 自动创建测试预订，用例后自动删除 |

## 框架特性

### 1. 接口方法层封装
用例层不直接调 `http.get/post`，而是调用 `booking_api.get_booking_list()` 等业务方法，语义清晰，接口变更只改 api 层一个文件。

### 2. 断言工具类
统一断言方法，报错信息规范，减少用例层重复代码，支持组合断言。

### 3. 日志系统
每个请求自动记录 URL、方法、请求体、响应状态码、响应体、耗时；每个用例自动记录开始/结束，方便排查问题。

### 4. Allure 报告
企业级美观报告，支持按功能模块分类、用例标题和描述、趋势图、详细错误信息。

### 5. 用例按功能细分
每个测试文件只测一个功能，职责单一，好找好改，多人协作不冲突。

### 6. 数据按模块拆分
测试数据按模块分文件存放，数据自描述（自带 remark 用例名），维护方便。

## 覆盖的测试场景

### 登录模块（test_auth.py）
- ✅ 正向登录成功
- ✅ 密码错误
- ✅ 用户名为空
- ✅ 密码为空
- ✅ 用户名不存在
- ✅ token 格式验证

### 预订查询（test_booking_query.py）
- ✅ 查询预订列表
- ✅ 查询预订详情（正常ID + 不存在的ID）

### 预订创建（test_booking_create.py）
- ✅ 完整数据创建预订
- ✅ 缺少可选字段
- ✅ 缺少必填字段 lastname

### 预订修改（test_booking_update.py）
- ✅ PUT 全量修改
- ✅ PATCH 部分修改（验证未修改字段保持不变）

### 预订删除（test_booking_delete.py）
- ✅ 删除预订成功
- ✅ 删除后查询返回404

### 权限测试（test_booking_auth.py）
- ✅ 未认证时修改返回403
