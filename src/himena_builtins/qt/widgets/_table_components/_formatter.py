from __future__ import annotations

from typing import Callable, Any


def _format_float(value, ndigits: int = 4) -> str:
    """convert string to int or float if possible"""
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value:.{ndigits}f}"
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_int(value, ndigits: int = 4) -> str:
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = str(value)
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_complex(value: complex, ndigits: int = 3) -> str:
    if value != value:  # nan
        text = "nan"
    elif 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value.real:.{ndigits}f}{value.imag:+.{ndigits}f}j"
    else:
        text = f"{value.real:.{ndigits-1}e}{value.imag:+.{ndigits-1}e}j"

    return text


def _format_datetime(value):
    return str(value)


_DEFAULT_FORMATTERS: dict[int, Callable[[Any], str]] = {
    "i": _format_int,
    "u": _format_int,
    "f": _format_float,
    "c": _format_complex,
    "t": _format_datetime,
}


def format_table_value(value: Any, fmt: str) -> str:
    return _DEFAULT_FORMATTERS.get(fmt, str)(value)
