from enum import Enum

class FunctionStatus(str, Enum):
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    IDLE = "IDLE"
    BUSY = "BUSY"
    TERMINATED = "TERMINATED"