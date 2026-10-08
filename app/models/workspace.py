from dataclasses import dataclass, field
from uuid import uuid4

from app.models.function_config import FunctionConfig

@dataclass
class Workspace:
    id: str = field(default_factory=lambda: str(uuid4()))
    config: FunctionConfig = field(default_factory=FunctionConfig)