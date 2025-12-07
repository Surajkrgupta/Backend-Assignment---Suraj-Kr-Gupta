import time
import threading

class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.http_requests = {}  # key: (path, status) -> count
        self.webhook_requests = {}  # key: result -> count
        self.latencies = []  # store ms values
    def inc_http(self, path, status):
        with self.lock:
            self.http_requests.setdefault((path, str(status)), 0)
            self.http_requests[(path, str(status))] += 1
    def inc_webhook(self, result):
        with self.lock:
            self.webhook_requests.setdefault(result, 0)
            self.webhook_requests[result] += 1
    def observe_latency(self, ms):
        with self.lock:
            self.latencies.append(ms)
    def render(self):
        lines = []
        with self.lock:
            for (path, status), v in self.http_requests.items():
                lines.append(f'http_requests_total{{path="{path}",status="{status}"}} {v}')
            for result, v in self.webhook_requests.items():
                lines.append(f'webhook_requests_total{{result="{result}"}} {v}')
            # simple latency buckets
            buckets = {"100":0,"500":0,"+Inf":0}
            for l in self.latencies:
                if l <= 100: buckets["100"] += 1
                if l <= 500: buckets["500"] += 1
                buckets["+Inf"] += 1
            for le, cnt in buckets.items():
                lines.append(f'request_latency_ms_bucket{{le="{le}"}} {cnt}')
            lines.append(f'request_latency_ms_count {len(self.latencies)}')
        return "\n".join(lines) + "\n"

metrics = Metrics()
