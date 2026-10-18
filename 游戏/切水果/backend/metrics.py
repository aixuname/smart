"""Bounded, thread-safe diagnostic windows; durations are milliseconds."""
from collections import defaultdict, deque
import math
import threading


class PipelineMetrics:
    def __init__(self, window=180):
        self.window = window
        self.samples = defaultdict(lambda: deque(maxlen=window))
        self.counts = defaultdict(int)
        self.lock = threading.Lock()

    def record(self, stage, milliseconds):
        if not math.isfinite(milliseconds) or milliseconds < 0:
            return
        with self.lock:
            self.samples[stage].append(milliseconds)

    def increment(self, name):
        with self.lock:
            self.counts[name] += 1

    def snapshot(self):
        with self.lock:
            values = {key: sorted(items) for key, items in self.samples.items() if items}
            counts = dict(self.counts)
        result = {}
        for stage, samples in values.items():
            result[stage] = {"p50": round(samples[int((len(samples) - 1) * 0.5)], 2),
                             "p95": round(samples[math.ceil((len(samples) - 1) * 0.95)], 2),
                             "samples": len(samples)}
        return {"stages_ms": result, "counts": counts, "window": self.window}
