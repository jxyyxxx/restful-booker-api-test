# ============================================================
# 接口方法层：预订相关接口
# 作用：封装预订模块所有接口的调用，用例层只调方法
# ============================================================

from common.http_client import http


class BookingAPI:
    """预订接口封装"""

    def get_booking_list(self):
        """查询预订列表"""
        return http.get("/booking")

    def get_booking_detail(self, booking_id):
        """
        查询预订详情
        :param booking_id: 预订ID
        """
        return http.get(f"/booking/{booking_id}")

    def create_booking(self, data):
        """
        创建预订
        :param data: 预订数据字典
        """
        return http.post("/booking", json=data)

    def update_booking(self, booking_id, data):
        """
        全量修改预订（PUT）
        :param booking_id: 预订ID
        :param data: 修改数据
        """
        return http.put(f"/booking/{booking_id}", json=data)

    def patch_booking(self, booking_id, data):
        """
        部分修改预订（PATCH）
        :param booking_id: 预订ID
        :param data: 部分修改数据
        """
        return http.patch(f"/booking/{booking_id}", json=data)

    def delete_booking(self, booking_id):
        """
        删除预订
        :param booking_id: 预订ID
        """
        return http.delete(f"/booking/{booking_id}")


# 全局实例，用例层直接导入使用
booking_api = BookingAPI()
