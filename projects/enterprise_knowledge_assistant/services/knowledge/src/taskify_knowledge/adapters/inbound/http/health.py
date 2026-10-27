"""Nonpublic aggregate operational counters contain no tenant identifiers, request text or credentials."""

import threading

from fastapi import FastAPI


class OperationalMetrics:
    """Maintain process-local request/readiness totals with fixed labels and bounded memory."""

    def __init__(self) -> None:
        """Initialize aggregate numeric counters without loading environment or touching dependencies."""
        self.lock = threading.Lock()
        self.values: dict[str, float] = {
            "requests_total": 0,
            "request_seconds_total": 0,
            "ready_checks_total": 0,
            "ready_failures_total": 0,
        }

    def request(self, status: int, elapsed: float) -> None:
        """Record only status class and elapsed time; never record bodies, paths, IDs or secret headers."""
        with self.lock:
            self.values["requests_total"] += 1
            self.values["request_seconds_total"] += max(0, elapsed)
            key = f"responses_{min(5, max(1, status // 100))}xx"
            self.values[key] = self.values.get(key, 0) + 1

    def readiness(self, successful: bool) -> None:
        """Track local readiness failures without retaining exception/provider details."""
        with self.lock:
            self.values["ready_checks_total"] += 1
            self.values["ready_failures_total"] += int(not successful)

    def snapshot(self) -> dict[str, float]:
        """Return a detached bounded aggregate snapshot safe for the private operator network."""
        with self.lock:
            return dict(self.values)


metrics = OperationalMetrics()


def install_metrics(app: FastAPI) -> None:
    """Expose aggregate counters only on the private service port; ingress blocks /metrics."""

    @app.get("/metrics", include_in_schema=False)
    def operational_metrics() -> dict[str, float]:
        """Return aggregate process counters without any company/chat/document/session data."""
        return metrics.snapshot()
