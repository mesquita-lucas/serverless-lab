from dataclasses import dataclass

@dataclass
class FunctionConfig:
    discount_threshold: float = 200.0
    discount_percent: float = 10.0
    processing_time_ms: int = 200
    cold_start_ms: int = 800
    max_instances: int = 10
    idle_timeout_seconds: int = 10