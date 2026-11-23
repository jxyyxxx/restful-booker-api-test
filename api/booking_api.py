# ============================================================
# 接口方法层：预订相关接口
# 作用：封装预订模块所有接口的调用，用例层只调方法
# ============================================================

from common.http_client import http


class BookingAPI:
    """预订接口封装"""

    def get_booking_list(self, params=None, headers=None):
        """
        查询预订列表
        :param params: 过滤条件，支持 firstname / lastname / checkin / checkout
        :param headers: 自定义请求头（内容协商测试用）
        """
        return http.get("/booking", params=params or None, headers=headers or None)

    def get_booking_detail(self, booking_id, headers=None):
        """
        查询预订详情
        :param booking_id: 预订ID
        :param headers: 自定义请求头（Accept: application/xml 等）
        """
        return http.get(f"/booking/{booking_id}", headers=headers or None)

    def create_booking(self, data, headers=None):
        """
        创建预订（JSON）
        :param data: 预订数据字典
        :param headers: 自定义请求头
        """
        return http.post("/booking", json=data, headers=headers or None)

    def create_booking_raw(self, body, content_type="text/xml", accept="application/json"):
        """
        用非 JSON 请求体创建预订（XML / 表单）
        :param body: 原始请求体字符串
        :param content_type: 请求头 Content-Type
        :param accept: 请求头 Accept，决定响应体格式
        """
        headers = {"Content-Type": content_type, "Accept": accept}
        return http.post("/booking", data=body, headers=headers)

    def update_booking(self, booking_id, data, headers=None):
        """
        全量修改预订（PUT）
        :param booking_id: 预订ID
        :param data: 修改数据
        :param headers: 自定义请求头（Basic 认证测试用）
        """
        return http.put(f"/booking/{booking_id}", json=data, headers=headers or None)

    def patch_booking(self, booking_id, data, headers=None):
        """
        部分修改预订（PATCH）
        :param booking_id: 预订ID
        :param data: 部分修改数据
        :param headers: 自定义请求头
        """
        return http.patch(f"/booking/{booking_id}", json=data, headers=headers or None)

    def delete_booking(self, booking_id, headers=None):
        """
        删除预订
        :param booking_id: 预订ID
        :param headers: 自定义请求头
        """
        return http.delete(f"/booking/{booking_id}", headers=headers or None)


# 全局实例，用例层直接导入使用
booking_api = BookingAPI()
