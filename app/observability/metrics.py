from collections import defaultdict

class Metrics:
    def __init__(self):
        self.data = defaultdict(self.default_metrics)

    def default_metrics(self):
        return {
            "requests": 0,
            "queued": 0,
            "processed": 0,
            "active_instances": 0,
            "cold_starts": 0,
            "errors": 0,
        }

    def increment(self, workspace_id: str, metric: str, value=1):
        self.data[workspace_id][metric] += value

    def set(self, workspace_id: str, metric: str, value):
        self.data[workspace_id][metric] = value

    def get(self, workspace_id: str):
        return self.data[workspace_id].copy()

    def reset(self, workspace_id: str):
        self.data[workspace_id] = self.default_metrics()