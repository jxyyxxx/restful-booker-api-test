# ============================================================
# 用例层：删除预订接口测试
# 覆盖：删除预订成功、删除后查询不到
# ============================================================

import allure
from common.api.booking_api import booking_api
from common.assert_utils import assert_utils
from common.utils import utils


@allure.feature("预订管理")
@allure.story("删除预订")
class TestBookingDelete:
    """删除预订接口测试"""

    @allure.title("删除预订")
    @allure.description("创建预订后删除，验证删除成功，删除后查询返回404")
    def test_delete_booking(self, admin_login):
        """
        删除预订接口测试
        自己创建测试数据，然后删除，验证删除成功
        注意：不使用 test_booking fixture（因为 fixture 后置也会删，会重复）
        """
        # 1. 先创建一条预订
        create_data = utils.random_booking_data()
        create_res = booking_api.create_booking(create_data)
        booking_id = create_res.json()["bookingid"]

        # 2. 执行删除
        delete_res = booking_api.delete_booking(booking_id)
        # restful-booker 删除成功返回 201
        assert delete_res.status_code == 201, \
            f"删除失败，状态码：{delete_res.status_code}（restful-booker 删除成功返回201）"

        # 3. 验证删除后查询不到
        query_res = booking_api.get_booking_detail(booking_id)
        assert_utils.assert_status_code(query_res, 404)
