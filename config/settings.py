# ============================================================
# 配置层：所有环境配置、全局常量统一放这里
# 作用：切换环境时只改 ENV 一个变量，用例代码完全不用动
# ============================================================

# 当前运行环境：local=本地Docker/Node部署，online=在线环境
ENV = "local"

# 各环境的配置字典
ENV_CONFIG = {
    "local": {
        "base_url": "http://localhost:3001",       # 本地restful-booker地址
        "admin_user": "admin",                        # 管理员账号
        "admin_pwd": "password123",                   # 管理员密码
    },
    "online": {
        "base_url": "https://restful-booker.herokuapp.com",  # 在线环境
        "admin_user": "admin",
        "admin_pwd": "password123",
    }
}

# 全局通用配置
REQUEST_TIMEOUT = 10          # 请求超时时间（秒）

# 日志配置
LOG_CONFIG = {
    "log_dir": "logs",                    # 日志文件存放目录
    "console_level": "INFO",              # 控制台输出级别（DEBUG/INFO/WARNING/ERROR）
    "file_level": "DEBUG",                # 文件输出级别（DEBUG/INFO/WARNING/ERROR）
    "log_format": "[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] %(message)s",  # 日志格式（含模块/函数/行号）
    "date_format": "%Y-%m-%d %H:%M:%S",  # 时间格式
}
