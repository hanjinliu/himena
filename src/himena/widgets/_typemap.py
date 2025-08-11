from __future__ import annotations

from typing import Any
from himena.consts import StandardType


class ObjectTypeMap:
    def __init__(self):
        self._functions = []

    def pick_type(self, value: Any) -> tuple[str, Any, Any]:
        for func in reversed(self._functions):
            out = func(value)
            if isinstance(out, tuple):
                typ, value_processed, meta = out
                if not isinstance(typ, str):
                    raise TypeError(
                        f"Object type map function {func} must return a str or a tuple "
                        f"of (str, Any, Any), got {out!r}."
                    )
            elif isinstance(out, str):
                typ, value_processed, meta = out, value, None
            elif out is None:
                continue
            else:
                raise TypeError(
                    f"Object type map function {func} must return a str or a tuple "
                    f"of (str, Any, Any), got {out!r}."
                )
            return typ, value_processed, meta
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
