from __future__ import annotations

from typing import Any
from himena.consts import StandardType


class ObjectTypeMap:
    def __init__(self):
        self._functions = []

    def pick_type(self, value: Any) -> str:
        for func in self._functions:
            out = func(value)
            if isinstance(out, str):
                return out
        raise ValueError(f"Could not determine the type of {value}.")

    def register(self, func):
        self._functions.append(func)
        return func


def register_defaults(map: ObjectTypeMap):
    import numpy as np
    from himena.workflow import Workflow

    @map.register
    def str_as_text(value: Any) -> str | None:
        if isinstance(value, str):
            return StandardType.TEXT
        return None

    @map.register
    def as_array(value) -> str | None:
        if isinstance(value, np.ndarray):
            if value.ndim == 2 and isinstance(value.dtype, np.dtypes.StringDType):
                return StandardType.TABLE
            return StandardType.ARRAY
        if hasattr(value, "__array__"):
            return StandardType.ARRAY
        return None

    @map.register
    def as_dataframe(value) -> str | None:
        if hasattr(value, "__dataframe__"):
            return StandardType.DATAFRAME
        return None

    @map.register
    def as_workflow(value) -> str | None:
        if isinstance(value, Workflow):
            return StandardType.WORKFLOW
        return None
