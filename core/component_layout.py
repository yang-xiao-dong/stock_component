# -*- coding: utf-8 -*-
"""外壳组件顺序的持久化；与组件的数据、计算和刷新无关。"""
import json
import logging
import os
import tempfile
import threading
from pathlib import Path

from core.data_define import ComponentLayout
from core.runtime_paths import user_data_path

logger = logging.getLogger(__name__)


def normalize_order(saved_order, available_ids):
    """忽略失效或重复项，新增组件按发现顺序追加。"""
    available = list(dict.fromkeys(available_ids))
    saved = saved_order if isinstance(saved_order, list) else []
    ordered = []
    for component_id in saved:
        if isinstance(component_id, str) and component_id in available and component_id not in ordered:
            ordered.append(component_id)
    return ordered + [component_id for component_id in available if component_id not in ordered]


class ComponentLayoutStore:
    def __init__(self, path=None):
        self._path = Path(path) if path is not None else user_data_path("data", "layout.json")
        self._lock = threading.Lock()

    def load(self, available_ids):
        with self._lock:
            try:
                payload = json.loads(self._path.read_text(encoding="utf-8"))
                layout = ComponentLayout.from_dict(payload) if isinstance(payload, dict) else None
                return normalize_order(layout.order if layout else None, available_ids)
            except FileNotFoundError:
                return list(available_ids)
            except (OSError, ValueError):
                logger.warning("组件排序配置无法读取，使用默认顺序", exc_info=True)
                return list(available_ids)

    def save(self, order, available_ids):
        available = list(available_ids)
        if (not isinstance(order, list) or not all(isinstance(item, str) for item in order)
                or len(order) != len(available) or set(order) != set(available)):
            return False
        temporary = None
        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self._path.parent,
                                                 prefix=".layout-", suffix=".tmp", delete=False) as output:
                    temporary = Path(output.name)
                    json.dump(ComponentLayout(order=list(order)).to_dict(), output, ensure_ascii=False, indent=2)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, self._path)
                return True
            except OSError:
                logger.warning("组件排序保存失败", exc_info=True)
                return False
            finally:
                if temporary is not None:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        logger.warning("无法清理排序配置临时文件：%s", temporary)
