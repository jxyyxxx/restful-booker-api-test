# ============================================================
# 工具层：日志/报告脱敏
# 作用：把请求体、响应体里的敏感字段替换成 ***，避免明文密码、token 落盘
#       （从原 common/utils.py 拆出）
# ============================================================

import re

# 需要脱敏的字段名（统一按小写比较）
SENSITIVE_KEYS = ("password", "token", "authorization", "cookie", "set-cookie")
MASK = "***"

# 匹配 JSON 文本里的敏感字段： "password": "xxx"
_JSON_PATTERN = r'("(?:password|token|authorization|cookie|set-cookie)"\s*:\s*")([^"]*)(")'


def mask_mapping(data):
    """对字典里的敏感字段脱敏（如登录密码、token），返回新字典，不修改入参"""
    if not isinstance(data, dict):
        return data

    masked = {}
    for key, value in data.items():
        if str(key).lower() in SENSITIVE_KEYS:
            masked[key] = MASK
        elif isinstance(value, dict):
            masked[key] = mask_mapping(value)
        else:
            masked[key] = value
    return masked


def mask_text(text):
    """对 JSON 文本里的敏感字段脱敏（用于打印响应体），非字符串原样返回"""
    if not isinstance(text, str):
        return text

    return re.sub(
        _JSON_PATTERN,
        lambda m: m.group(1) + MASK + m.group(3),
        text,
        flags=re.IGNORECASE,
    )


def mask(data):
    """按类型自动选择脱敏方式：dict 走字段脱敏，str 走文本脱敏"""
    if isinstance(data, dict):
        return mask_mapping(data)
    if isinstance(data, str):
        return mask_text(data)
    return data
