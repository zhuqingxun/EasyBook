"""统计收集与持久化服务"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

_MAX_RESPONSE_TIMES = 1000
_MAX_SEARCH_TERMS = 100
_MAX_HOURLY_DAYS = 7


class StatsService:
    """收集搜索统计、访问量统计，支持 JSON 文件持久化"""

    def __init__(self):
        self._lock = Lock()
        self.search_count = 0
        self.search_terms: Counter = Counter()
        self.response_times: list[float] = []
        self.hourly_pv: defaultdict[str, int] = defaultdict(int)
        self.daily_pv: defaultdict[str, int] = defaultdict(int)
        self.unique_ips: set[str] = set()
        self.total_pv = 0

    def record_search(self, query: str, response_time: float, ip: str) -> None:
        with self._lock:
            self.search_count += 1
            self.search_terms[query.lower().strip()] += 1
            # 保留 top N
            if len(self.search_terms) > _MAX_SEARCH_TERMS * 2:
                self.search_terms = Counter(
                    dict(self.search_terms.most_common(_MAX_SEARCH_TERMS))
                )
            # 环形缓冲
            self.response_times.append(response_time)
            if len(self.response_times) > _MAX_RESPONSE_TIMES:
                self.response_times = self.response_times[-_MAX_RESPONSE_TIMES:]
            self.unique_ips.add(ip)

    def record_request(self, ip: str) -> None:
        now = datetime.now(tz=timezone.utc)
        hour_key = now.strftime("%Y-%m-%dT%H")
        day_key = now.strftime("%Y-%m-%d")
        with self._lock:
            self.total_pv += 1
            self.hourly_pv[hour_key] += 1
            self.daily_pv[day_key] += 1
            self.unique_ips.add(ip)
            self._cleanup_old_pv(now)

    def _cleanup_old_pv(self, now: datetime) -> None:
        """清理超过 7 天的小时级 PV 数据"""
        cutoff = now.strftime("%Y-%m-%d")
        # 简单策略：保留最近 7*24=168 个小时 key
        if len(self.hourly_pv) > _MAX_HOURLY_DAYS * 24:
            sorted_keys = sorted(self.hourly_pv.keys())
            excess = len(sorted_keys) - _MAX_HOURLY_DAYS * 24
            for k in sorted_keys[:excess]:
                del self.hourly_pv[k]

    def get_stats(self) -> dict:
        with self._lock:
            avg_time = (
                round(sum(self.response_times) / len(self.response_times), 2)
                if self.response_times
                else 0
            )
            top_terms = self.search_terms.most_common(20)
            # 最近 24 小时 PV 趋势
            sorted_hourly = sorted(self.hourly_pv.items())[-24:]
            # 最近 7 天 PV 趋势
            sorted_daily = sorted(self.daily_pv.items())[-7:]
            return {
                "search_count": self.search_count,
                "top_search_terms": [
                    {"term": t, "count": c} for t, c in top_terms
                ],
                "avg_response_time": avg_time,
                "total_pv": self.total_pv,
                "unique_visitors": len(self.unique_ips),
                "hourly_pv": [{"hour": h, "count": c} for h, c in sorted_hourly],
                "daily_pv": [{"date": d, "count": c} for d, c in sorted_daily],
            }

    def save_to_file(self, path: str) -> None:
        data = {
            "search_count": self.search_count,
            "search_terms": dict(self.search_terms.most_common(_MAX_SEARCH_TERMS)),
            "total_pv": self.total_pv,
            "hourly_pv": dict(self.hourly_pv),
            "daily_pv": dict(self.daily_pv),
            "unique_ips": list(self.unique_ips),
        }
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("统计数据已保存: %s", path)
        except Exception:
            logger.exception("统计数据保存失败: path=%s", path)

    def load_from_file(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            logger.info("统计数据文件不存在，跳过加载: %s", path)
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            with self._lock:
                self.search_count = data.get("search_count", 0)
                self.search_terms = Counter(data.get("search_terms", {}))
                self.total_pv = data.get("total_pv", 0)
                self.hourly_pv = defaultdict(int, data.get("hourly_pv", {}))
                self.daily_pv = defaultdict(int, data.get("daily_pv", {}))
                self.unique_ips = set(data.get("unique_ips", []))
            logger.info("统计数据已加载: %s", path)
        except Exception:
            logger.exception("统计数据加载失败: path=%s", path)


stats_service = StatsService()
