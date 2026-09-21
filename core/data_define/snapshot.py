# -*- coding: utf-8 -*-
"""收盘快照契约：某交易日收盘后的完整原始数据，用于离线加载/回放。

设计要点：
- 只存原始数据（实时行情 + 分时 + 日K）；组合聚合结构（GroupMinute/
  GroupKline/Contribution）是纯函数结果，可由快照经 core/group_calc
  离线重算，不冗余存储
- version 字段留作格式演进；from_dict 容错（缺字段为 None、未知字段忽略）
- 存储位置：data/snapshots/<date>.json（已被 .gitignore 排除）

后期离线用法示意：
    snap = load_snapshot("2026-09-18")
    minute = group_calc.build_group_minute(snap.minute, prev_closes, shares, PRINCIPAL)
"""
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List

from core.runtime_paths import user_data_path

from .common import Contract
from .kline import KlineBar
from .minute import MinutePoint
from .quote import RealtimeQuote

SNAPSHOT_VERSION = 1

SNAPSHOT_DIR = str(user_data_path("data", "snapshots"))


@dataclass
class MarketSnapshot(Contract):
    version: int = SNAPSHOT_VERSION
    date: str = None                                  # 交易日 yyyy-mm-dd
    saved_at: str = None                              # 保存时间
    realtime: Dict[str, RealtimeQuote] = field(default_factory=dict)   # {code: 行情}
    minute: Dict[str, List[MinutePoint]] = field(default_factory=dict)  # {code: 分时}
    kline: Dict[str, List[KlineBar]] = field(default_factory=dict)     # {code: 日K}

    @classmethod
    def capture(cls, realtime, minute, kline):
        """由生产端的 dict 数据组装快照（date 取日K最后一根的日期）"""
        dates = sorted({b.get("date") for bars in kline.values() for b in bars
                        if b.get("date")})
        return cls(
            version=SNAPSHOT_VERSION,
            date=dates[-1] if dates else time.strftime("%Y-%m-%d"),
            saved_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            realtime={c: RealtimeQuote.from_dict(q) for c, q in realtime.items() if q},
            minute={c: [MinutePoint.from_dict(p) for p in pts]
                    for c, pts in minute.items()},
            kline={c: [KlineBar.from_dict(b) for b in bars]
                   for c, bars in kline.items()},
        )

    @classmethod
    def from_dict(cls, d: dict):
        if not d:
            return None
        return cls(
            version=int(d.get("version", SNAPSHOT_VERSION)),
            date=d.get("date"),
            saved_at=d.get("saved_at"),
            realtime={c: RealtimeQuote.from_dict(q)
                      for c, q in (d.get("realtime") or {}).items()},
            minute={c: [MinutePoint.from_dict(p) for p in pts]
                    for c, pts in (d.get("minute") or {}).items()},
            kline={c: [KlineBar.from_dict(b) for b in bars]
                   for c, bars in (d.get("kline") or {}).items()},
        )


def snapshot_path(date: str) -> str:
    """某交易日的快照文件路径（data/snapshots/<date>.json）"""
    return os.path.join(SNAPSHOT_DIR, f"{date}.json")


def save_snapshot(snapshot: MarketSnapshot, path: str = None) -> str:
    """保存快照为 JSON，返回文件路径"""
    path = path or snapshot_path(snapshot.date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot.to_dict(), f, ensure_ascii=False)
    return path


def load_snapshot(date_or_path: str) -> MarketSnapshot:
    """加载快照：传交易日（2026-09-18）或完整文件路径"""
    if os.path.isabs(date_or_path) or date_or_path.endswith(".json"):
        path = date_or_path
    else:
        path = snapshot_path(date_or_path)
    with open(path, encoding="utf-8") as f:
        return MarketSnapshot.from_dict(json.load(f))
