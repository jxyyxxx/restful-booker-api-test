# ============================================================
# 数据加载工具类
# 作用：读取 YAML 格式的测试数据，自动提取用例名
# 优势：数据与代码分离，非技术人员也能编辑测试数据
# ============================================================

import os
import yaml


class DataLoader:
    """YAML 测试数据加载器"""

    def __init__(self, yaml_dir=None):
        """
        初始化
        :param yaml_dir: YAML 文件目录，不传则用默认的 data/yaml
        """
        if yaml_dir is None:
            # 默认路径：项目根目录下的 data/yaml
            self.yaml_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "yaml"
            )
        else:
            self.yaml_dir = yaml_dir

    def load(self, filename, key=None):
        """
        读取 YAML 文件
        :param filename: 文件名，比如 "login_data.yaml"
        :param key: 要读取的子节点 key，比如 booking_data.yaml 里的 "create"、"query"
        :return: 数据列表
        """
        filepath = os.path.join(self.yaml_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 如果指定了 key，就读取子节点
        if key is not None:
            if key not in data:
                raise KeyError(f"YAML 文件 {filename} 中找不到 key: {key}")
            data = data[key]

        return data

    def get_test_data(self, filename, key=None):
        """
        读取测试数据，自动提取 case_name 作为用例名（ids）
        直接可以给 @pytest.mark.parametrize 使用
        :param filename: 文件名
        :param key: 子节点 key（可选）
        :return: (data_list, ids_list)
        """
        data = self.load(filename, key)

        # 自动提取 case_name 作为用例名
        # 如果没有 case_name 字段，就用索引作为名字
        ids = []
        for i, item in enumerate(data):
            if isinstance(item, dict) and "case_name" in item:
                ids.append(item["case_name"])
            else:
                ids.append(f"用例{i+1}")

        return data, ids


# 全局实例，其他模块直接导入使用
data_loader = DataLoader()
