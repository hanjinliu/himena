from __future__ import annotations

from functools import reduce
import operator
from typing import Any, Sequence, TYPE_CHECKING

from app_model.types import KeyBindingRule
from app_model.expressions import BoolOp

from himena._app_model import AppContext as ctx

if TYPE_CHECKING:
    KeyBindingsType = str | KeyBindingRule | Sequence[str] | Sequence[KeyBindingRule]
    PluginConfigType = Any


def expr_and(expr: BoolOp | None, other: BoolOp) -> BoolOp:
    if expr is None:
        return other
    return expr & other


def types_to_expression(types: list[str]) -> BoolOp:
    return reduce(operator.or_, map(type_to_expression, types))


def type_to_expression(typ: str) -> BoolOp:
    subtypes = typ.split(".")
    nsub = len(subtypes)
    out = ctx.active_window_model_type == subtypes[0]
    if nsub >= 2:
        out &= ctx.active_window_model_subtype_1 == subtypes[1]
        if nsub >= 3:
            out &= ctx.active_window_model_subtype_2 == subtypes[2]
            if nsub >= 4:
                out &= ctx.active_window_model_subtype_3 == subtypes[3]
                if nsub >= 5:
                    raise ValueError(f"The maximum number of subtypes are 4, got {typ}")
    return out


def is_model_menu_prefix(menu_id: str) -> bool:
    ids = menu_id.split("/")
    if len(ids) < 3:
        return False
    return (ids[0], ids[1]) == ("", "model_menu")
