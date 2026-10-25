# ============================================================
# 配置层：所有环境配置、全局常量统一放这里
# 设计要点：
#   1. 环境由环境变量 ENV 决定，默认 local；白名单校验，写错环境名直接报错
#   2. base_url / 管理员账号支持环境变量覆盖，切环境不用改代码
#      （CI 的 workflow 里声明了 BASE_URL，这里读取后那行才真正生效）
# ============================================================

import os

# 项目根目录：报告模块用它定位 git 仓库（取框架自身 commit）、拼绝对路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 允许的环境白名单。本项目只跑本地服务（npm start 或 docker compose），不再保留在线环境
ALLOWED_ENVS = ("local",)

# 当前运行环境：local = 本地 restful-booker（默认 http://localhost:3001）
ENV = os.getenv("ENV", "local")
if ENV not in ALLOWED_ENVS:
    raise ValueError(f"未知环境 ENV={ENV}，可选值：{ALLOWED_ENVS}")

# 各环境的默认配置（单项可被同名环境变量覆盖，见下方导出的变量）
ENV_CONFIG = {
    "local": {
        "base_url": "http://localhost:3001",       # 本地 restful-booker 地址
        "admin_user": "admin",                     # 管理员账号
        "admin_pwd": "password123",                # 管理员密码
    },
}

# 对外导出的最终配置：优先级 环境变量 > ENV_CONFIG 默认值
BASE_URL = os.getenv("BASE_URL", ENV_CONFIG[ENV]["base_url"])
ADMIN_USER = os.getenv("ADMIN_USER", ENV_CONFIG[ENV]["admin_user"])
ADMIN_PWD = os.getenv("ADMIN_PWD", ENV_CONFIG[ENV]["admin_pwd"])

# 全局通用配置
REQUEST_TIMEOUT = 3  # 请求超时时间（秒）

# 响应时间门禁：单次请求耗时的上限（秒），可用环境变量 RESPONSE_TIME_LIMIT 覆盖
# 取值说明：本地实测平均 2~20ms，500ms 约为实测值的 25 倍以上，
RESPONSE_TIME_LIMIT = float(os.getenv("RESPONSE_TIME_LIMIT", "0.5"))

# 日志配置
LOG_CONFIG = {
    "log_dir": "logs",                    # 日志文件存放目录
    "console_level": "INFO",              # 控制台输出级别（DEBUG/INFO/WARNING/ERROR）
    "file_level": "DEBUG",                # 文件输出级别（DEBUG/INFO/WARNING/ERROR）
    "log_format": "[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",  # 日志格式（含模块/函数/行号）
    "date_format": "%Y-%m-%d %H:%M:%S",  # 时间格式
}
