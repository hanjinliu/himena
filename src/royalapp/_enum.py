import sys
from enum import Enum

__all__ = ["StrEnum"]

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        pass
