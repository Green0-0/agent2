import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

class HistoryRecord:
    """A single recorded event in the API history."""

    def __init__(
        self,
        endpoint: str,
        action: Optional[str],
        request_data: Any,
        parsed_data: Any,
        response_data: Optional[Any],
        extracted_response: Optional[Any],
        errors: List[str],
        latency_ms: float,
        success: bool,
    ):
        self.timestamp = time.time()
        self.endpoint = endpoint
        self.action = action
        self.request_data = request_data
        self.parsed_data = parsed_data
        self.response_data = response_data
        self.extracted_response = extracted_response
        self.errors = errors
        self.latency_ms = latency_ms
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "endpoint": self.endpoint,
            "action": self.action,
            "request_data": self.request_data,
            "parsed_data": self.parsed_data,
            "response_data": self.response_data,
            "extracted_response": self.extracted_response,
            "errors": self.errors,
            "latency_ms": self.latency_ms,
            "success": self.success,
        }


class StatsTracker:
    """Aggregates statistics for a single endpoint."""

    def __init__(self):
        self._lock = threading.Lock()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tool_calls = 0
        self.tool_usage = defaultdict(int)
        self.errors_by_type = defaultdict(int)
        self.action_counts = defaultdict(int)
        self.latency_sum_ms = 0.0
        self.latency_min_ms = float("inf")
        self.latency_max_ms = 0.0
        self.requests_with_tools = 0
        self.requests_without_tools = 0
        self.start_time = time.time()

    def reset(self) -> None:
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tool_calls = 0
        self.tool_usage.clear()
        self.errors_by_type.clear()
        self.action_counts.clear()
        self.latency_sum_ms = 0.0
        self.latency_min_ms = float("inf")
        self.latency_max_ms = 0.0
        self.requests_with_tools = 0
        self.requests_without_tools = 0
        self.start_time = time.time()

    def record(self, record: HistoryRecord) -> None:
        with self._lock:
            self.total_requests += 1
            if record.success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            self.latency_sum_ms += record.latency_ms
            self.latency_min_ms = min(self.latency_min_ms, record.latency_ms)
            self.latency_max_ms = max(self.latency_max_ms, record.latency_ms)

            if record.action:
                self.action_counts[record.action] += 1

            extracted = record.extracted_response or {}
            tool_calls = []
            if isinstance(extracted, dict):
                tool_calls = extracted.get("tool_calls", []) or []

            if record.endpoint == "openai":
                if tool_calls:
                    self.requests_with_tools += 1
                else:
                    self.requests_without_tools += 1

            self.total_tool_calls += len(tool_calls)
            for tc in tool_calls:
                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                self.tool_usage[fn.get("name", "unknown")] += 1

            for err in record.errors:
                self.errors_by_type[err] += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = (
                self.latency_sum_ms / self.total_requests
                if self.total_requests > 0
                else 0.0
            )
            return {
                "uptime_seconds": time.time() - self.start_time,
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": (
                    self.successful_requests / self.total_requests
                    if self.total_requests > 0
                    else 0.0
                ),
                "total_tool_calls": self.total_tool_calls,
                "tool_usage": dict(self.tool_usage),
                "errors_by_type": dict(self.errors_by_type),
                "action_counts": dict(self.action_counts),
                "latency_avg_ms": avg_latency,
                "latency_min_ms": self.latency_min_ms
                if self.latency_min_ms != float("inf")
                else 0.0,
                "latency_max_ms": self.latency_max_ms,
                "requests_with_tools": self.requests_with_tools,
                "requests_without_tools": self.requests_without_tools,
            }


class HistoryStore:
    """Thread-safe in-memory store for history records and per-endpoint stats."""

    def __init__(self, max_size: int = 1000):
        self._lock = threading.Lock()
        self._records: deque = deque(maxlen=max_size)
        self.stats_openai = StatsTracker()
        self.stats_custom = StatsTracker()

    def add(self, record: HistoryRecord) -> None:
        with self._lock:
            self._records.append(record)
        if record.endpoint == "openai":
            self.stats_openai.record(record)
        else:
            self.stats_custom.record(record)

    def get_records(
        self, endpoint: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._lock:
            records = list(self._records)
        if endpoint:
            records = [r for r in records if r.endpoint == endpoint]
        records = records[-limit:][::-1]  # most recent first
        return [r.to_dict() for r in records]

    def get_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        if endpoint == "openai":
            return self.stats_openai.get_stats()
        elif endpoint == "custom":
            return self.stats_custom.get_stats()
        return {
            "openai": self.stats_openai.get_stats(),
            "custom": self.stats_custom.get_stats(),
        }

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self.stats_openai.reset()
            self.stats_custom.reset()

_history_store: Optional[HistoryStore] = None
_history_lock = threading.Lock()

def get_history_store() -> HistoryStore:
    global _history_store
    if _history_store is None:
        with _history_lock:
            if _history_store is None:
                _history_store = HistoryStore()
    return _history_store

def _err_to_str(e) -> str:
    """Normalize an error (str or Enum) to a string."""
    if hasattr(e, "name"):
        return e.name
    return str(e)