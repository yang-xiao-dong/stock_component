# -*- coding: utf-8 -*-
"""数据契约基类：所有数据结构的唯一定义工具。

约定：
- 每个数据域一个文件（quote/kline/minute/stock/group/snapshot）
- 生产端（stock_api / group_calc / 组件）必须经这些定义构造输出，
  前端字段名以 to_dict() 的键为准
- from_dict 容错：缺失字段为 None、未知字段忽略（向前兼容），
  供后期快照加载旧版本数据使用
"""
from dataclasses import asdict, fields


class Contract:

    def to_dict(self) -> dict:
        """递归序列化（嵌套 dataclass / list / dict 全部展开为纯 JSON 结构）"""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        """由 dict 重建；缺失字段为 None，未知字段忽略"""
        if not d:
            return None
        return cls(**{f.name: d.get(f.name) for f in fields(cls)})
