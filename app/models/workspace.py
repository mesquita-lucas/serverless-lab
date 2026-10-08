import time
from dataclasses import dataclass, field
from uuid import uuid4

from app.models.function_config import FunctionConfig 

@dataclass
class Workspace:
    id: str = field(
        default_factory=lambda: str(uuid4())
    )

    config: FunctionConfig = field(
        default_factory=FunctionConfig
    )

    last_activity: float = field(
        default_factory=time.monotonic
    )

    def touch(self):
        self.last_activity = time.monotonic()