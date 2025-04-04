from __future__ import annotations
from typing import Any
import numpy as np
from himena.consts import StandardType
from himena.plugins import (
    ReproduceArgs,
    register_modification_tracker,
    register_hidden_function,
)
from himena.types import Parametric, WidgetDataModel


@register_hidden_function(command_id="builtins:user-modification:text")
def reproduce_text_modification(model: WidgetDataModel) -> Parametric:
    if not isinstance(model.value, str):
        raise TypeError("Model value must be a string")

    def run(diff: list[tuple[str, int, int, str]]) -> WidgetDataModel:
        old_text = model.value
        new_text = old_text
        offset = 0
        for tag, i1, i2, new_part in diff:
            i1 += offset
            i2 += offset
            if tag == "!":
                new_text = new_text[:i1] + new_part + new_text[i2:]
                offset += len(new_part) - (i2 - i1)
            elif tag == "-":
                new_text = new_text[:i1] + new_text[i2:]
                offset -= i2 - i1
            elif tag == "+":
                new_text = new_text[:i1] + new_part + new_text[i1:]
                offset += len(new_part)
        model.value = new_text
        return model

    return run


USE_DIFFLIB_LIMIT = 1000  # Limit for the number of characters to switch to difflib


@register_modification_tracker(type=StandardType.TEXT)
def text_modification_tracker(old: str, new: str) -> ReproduceArgs:
    """Track modifications to text widgets."""
    import difflib

    if len(new) < USE_DIFFLIB_LIMIT:
        if old.startswith(new):
            diff = [("-", 0, len(old), "")]
        elif new.startswith(old):
            diff = [("+", 0, len(old), new)]
        else:
            diff = [("!", 0, len(old), new)]
    else:
        # Get the diff between the old and new text
        diff: list[tuple[str, int, int, str]] = []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, old, new
        ).get_opcodes():
            if tag == "replace":
                diff.append(("!", i1, i2, new[j1:j2]))
            elif tag == "delete":
                diff.append(("-", i1, i2, ""))
            elif tag == "insert":
                diff.append(("+", i1, i2, new[j1:j2]))

    # Create the ReproduceArgs object
    return ReproduceArgs(
        command_id="builtins:user-modification:text",
        with_params={"diff": diff},
    )


@register_hidden_function(command_id="builtins:user-modification:table")
def reproduce_table_modification(model: WidgetDataModel) -> Parametric:
    def run(diff: dict[str, list[Any]]) -> WidgetDataModel:
        if "array" in diff:
            model.value = np.array(diff["array"], dtype=np.dtypes.StringDType())
        else:
            shape = diff["shape"]
            out = np.zeros(shape, dtype=np.dtypes.StringDType())
            r0, c0 = model.value.shape
            out[: max(out.shape[0], r0), : max(out.shape[1], c0)] = model.value
            for row, col, value in zip(diff["rows"], diff["cols"], diff["values"]):
                out[row, col] = value
        return model

    return run


@register_modification_tracker(type=StandardType.TABLE)
def table_modification_tracker(old: np.ndarray, new: np.ndarray) -> ReproduceArgs:
    """Track modifications to table widgets."""
    if new.size < 100 or new.size > old.size * 2:
        diff = {"array": new.tolist()}
    else:
        old_normed = old.copy()
        r0, c0 = old.shape
        if old.shape[0] > new.shape[0]:
            old_normed = old_normed[: new.shape[0]]
        elif old.shape[0] < new.shape[0]:
            old_normed = np.vstack(
                (old_normed, np.zeros((new.shape[0] - r0, c0), dtype=old_normed.dtype))
            )
        if old.shape[1] > new.shape[1]:
            old_normed = old_normed[:, : new.shape[1]]
        elif old.shape[1] < new.shape[1]:
            old_normed = np.hstack(
                (old_normed, np.zeros((r0, new.shape[1] - c0), dtype=old_normed.dtype))
            )

        rows, cols = np.where(old_normed.shape != new.shape)
        if len(rows) * 3 > new.size:
            diff = {"array": new.tolist()}
        else:
            diff = {
                "shape": new.shape,
                "rows": rows.tolist(),
                "cols": cols.tolist(),
                "values": new[rows, cols].tolist(),
            }
    # Create the ReproduceArgs object
    return ReproduceArgs(
        command_id="builtins:user-modification:table",
        with_params={"diff": diff},
    )
