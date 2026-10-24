"""统一采集与回放服务。在线也从已提交的版本读取；离线分支不访问 provider。"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from config import REFRESH
from core.data_define.history import ReplayContext, HistoryStatus
from .settings import current_config, requirements
from .store import valid_date, utc_now

class HistoryService:
    def __init__(self, store, provider, settings=current_config):
        self.store, self.provider, self.settings = store, provider, settings
        self._lock = threading.RLock()
        self._quote_lock = threading.Lock()
        self._collect_lock = threading.Lock()
        self._stream_locks = {}
        self._cache = {}             # stream -> (monotonic, dataset_id, requested_count)
        self._replay = None
        self._generation = 0
        self._failures = {}
        self._quote_attempt = 0
        self._quote_result = {}

    def mode(self):
        with self._lock:
            return {"mode": "offline" if self._replay else "live",
                    "date": self._replay.date if self._replay else None}

    def config(self, name, default):
        with self._lock:
            return deepcopy(self._replay.config.get(name, default) if self._replay else default)

    def generation(self):
        with self._lock:
            return self._generation

    def context_key(self):
        with self._lock:
            return (self._generation, "offline" if self._replay else "live",
                    self._replay.date if self._replay else None)

    def set_mode(self, mode, date=None):
        if mode == "live":
            with self._lock:
                self._replay = None
                self._generation += 1
                self._cache.clear()
                self._quote_attempt = 0
            return True
        if mode != "offline":
            return False
        try:
            date = valid_date(date)
            if date not in self.store.dates():
                return False
            context = self.store.replay(date)
            if context is None:
                settings = self.store.profile_at(date) or self.settings()
                refs = {stream: self.store.latest(stream.split(":")[1], stream.split(":")[0], date=date)
                        for stream in requirements(settings)}
                context = ReplayContext(date=date, config=settings,
                                        datasets={key: val for key, val in refs.items() if val},
                                        missing=[key for key, val in refs.items() if not val], origin="reconstructed")
            with self._lock:
                self._replay = context
                self._generation += 1
            return True
        except (ValueError, TypeError):
            return False

    def _state(self):
        with self._lock:
            return self._generation, self._replay

    def _failure(self, code, kind, config, error):
        self.store.record_failure(code, kind, config, error)
        with self._lock:
            self._failures[f"{kind}:{code}"] = str(error)

    def _save(self, batch, config, count):
        identity = self.store.save_batch(batch, config)
        with self._lock:
            key = f"{batch.kind}:{batch.code}"
            self._cache[key] = (time.monotonic(), identity, count)
            self._failures.pop(key, None)
        return identity

    def _cached(self, stream, interval, count=None):
        with self._lock:
            entry = self._cache.get(stream)
            if entry and time.monotonic() - entry[0] < interval and (count is None or (entry[2] or 0) >= count):
                return entry[1]
        return None

    def _quote_ids(self, codes, force=False):
        with self._quote_lock:
            if self._state()[1]:
                return {}
            settings = self.settings()
            all_codes = sorted(set(codes) | {key.split(":", 1)[1] for key in requirements(settings)
                                            if key.startswith("quote:")})
            if not force and all(self._cached(f"quote:{c}", REFRESH["realtime"]) for c in codes):
                return {c: self._cached(f"quote:{c}", REFRESH["realtime"]) for c in codes}
            if not force and time.monotonic() - self._quote_attempt < REFRESH["realtime"]:
                return {c: self._quote_result[c] for c in codes if c in self._quote_result}
            try:
                batches = self.provider.get_quote_batches(all_codes)
            except (OSError, ValueError):
                batches = {}
            ids = {}
            for code in all_codes:
                try:
                    batch = batches.get(code)
                    if not batch:
                        raise ValueError("行情接口没有返回该股票")
                    ids[code] = self._save(batch, settings, None)
                except (ValueError, TypeError, KeyError) as exc:
                    self._failure(code, "quote", settings, exc)
            self._quote_attempt, self._quote_result = time.monotonic(), ids
            return {code: ids[code] for code in codes if code in ids}

    def quotes(self, codes):
        generation, replay = self._state()
        if replay:
            refs = {code: replay.datasets.get(f"quote:{code}") for code in codes}
        else:
            refs = self._quote_ids(codes)
        result = {}
        for code, identity in refs.items():
            rows = self.store.read(identity, end_date=replay.date if replay else None)
            if rows:
                result[code] = rows[0]
        return result if generation == self.generation() else {}

    def _series_id(self, kind, code, count=None, force=False):
        stream = f"{kind}:{code}"
        settings = self.settings()
        requested = max(count or 0, requirements(settings).get(stream) or 0) or None
        with self._lock:
            lock = self._stream_locks.setdefault(stream, threading.Lock())
        with lock:
            if self._state()[1]:
                return None
            interval = REFRESH["minute" if kind == "minute" else "kline"]
            cached = self._cached(stream, interval, requested)
            if cached and not force:
                return cached
            try:
                fetch = getattr(self.provider, f"get_{kind}_batch")
                batch = fetch(code) if kind == "minute" else fetch(code, requested)
                if not batch:
                    raise ValueError("接口未返回有效数据")
                return self._save(batch, settings, requested)
            except (ValueError, TypeError, KeyError, OSError) as exc:
                self._failure(code, kind, settings, exc)
                return None

    def series(self, kind, code, count=None):
        generation, replay = self._state()
        identity = replay.datasets.get(f"{kind}:{code}") if replay else self._series_id(kind, code, count)
        rows = self.store.read(identity, count=count, end_date=replay.date if replay else None)
        return rows if generation == self.generation() else []

    def collect(self, force=False):
        """采集全组件需求并固定本轮引用；部分成功仍入库，缺失清单随回放保存。"""
        with self._collect_lock:
            generation, replay = self._state()
            if replay:
                return {"ok": False, "error": "离线模式不发起网络采集"}
            settings = self.settings()
            needs = requirements(settings)
            codes = [key.split(":", 1)[1] for key in needs if key.startswith("quote:")]
            refs = {f"quote:{code}": identity for code, identity in self._quote_ids(codes, force).items()}
            tasks = [(key, count) for key, count in needs.items() if not key.startswith("quote:")]
            def fetch(item):
                key, count = item
                return key, self._series_id(*key.split(":"), count=count, force=force)
            with ThreadPoolExecutor(max_workers=4) as pool:
                refs.update({key: identity for key, identity in pool.map(fetch, tasks) if identity})
            if generation != self.generation():
                return {"ok": False, "error": "数据模式已切换，本轮未发布回放"}
            days = [self.store.info(refs[f"quote:{s['code']}"])["end_date"]
                    for s in settings["STOCKS"] if f"quote:{s['code']}" in refs]
            if not days:
                return {"ok": False, "error": "组内行情获取失败，已取得的其他数据仍已入库"}
            day = max(days)
            missing = [key for key in needs if key not in refs]
            # 当日A股报价/分时必须同日；美股参照保留自身交易日，不冒充A股同日。
            for key, identity in list(refs.items()):
                kind, code = key.split(":")
                info = self.store.info(identity)
                if (kind in ("quote", "minute") and not code.startswith("us") and info["end_date"] != day
                        or info["end_date"] > day):
                    missing.append(f"日期不匹配 {key}: {info['end_date']}")
                    del refs[key]
                elif needs[key] and info["row_count"] < needs[key]:
                    missing.append(f"窗口不足 {key}: {info['row_count']}/{needs[key]}")
            context = ReplayContext(date=day, saved_at=utc_now(), datasets=refs, config=settings, missing=missing)
            self.store.save_replay(context)
            if force:
                with self._lock:
                    self._generation += 1
            return {"ok": True, "date": day, "path": str(self.store.path), "missing": missing,
                    "complete": not missing}

    def status(self):
        with self._lock:
            replay = self._replay
            if replay:
                message = "历史数据重建，缺失项不联网补齐" if replay.origin == "reconstructed" else "已固定历史数据版本"
                return HistoryStatus(mode="offline", date=replay.date, saved_at=replay.saved_at,
                                     missing=list(replay.missing), message=message).to_dict()
            return HistoryStatus(missing=[f"{key}: {value}" for key, value in self._failures.items()],
                                 message="在线采集自动入库").to_dict()
