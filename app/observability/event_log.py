from collections import defaultdict
from datetime import datetime

class EventLog:
    def __init__(self):
        self.logs = defaultdict(list)

    def add(self, workspace_id: str, event: str, data=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {},
        }

        self.logs[workspace_id].append(entry)

        return entry

    def get(self, workspace_id: str):
        return self.logs[workspace_id]

    def clear(self, workspace_id: str):
        self.logs[workspace_id] = []