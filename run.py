# ============================================================
# 执行入口：一键运行测试
# 作用：封装 pytest 执行命令，不用每次敲长串指令
#      直接右键运行这个文件即可执行测试
# 注意：Allure 报告的生成和打开由 conftest.py 的钩子自动完成
# ============================================================

import os
import sys
import pytest

# 把项目根目录加入 Python 路径，解决 import 问题
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    # ========== 执行配置（取消注释切换执行方式） ==========

    # 方式1：执行所有用例（默认）
    pytest.main([
        "-v",
        "--alluredir=reports/allure-results",
        "--clean-alluredir"
    ])

    # 方式2：只执行登录模块
    # pytest.main(["-v", "testcases/test_auth.py"])

    # 方式3：只执行预订模块
    # pytest.main(["-v", "testcases/booking/"])

    # 方式4：只执行冒烟用例
    # pytest.main(["-v", "-m", "smoke"])

    # ========== 说明 ==========
    # 测试结束后，conftest.py 中的 pytest_sessionfinish 钩子会自动：
    # 1. 调用 allure generate 生成 HTML 报告
    # 2. 调用 allure open 启动本地服务并在浏览器打开报告
    # 所以这里不需要再手动生成报告了
