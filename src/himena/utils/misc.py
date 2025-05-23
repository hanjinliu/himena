from __future__ import annotations

import re
from typing import (
    TypeVar,
    Iterator,
    NamedTuple,
    Callable,
    overload,
    TYPE_CHECKING,
    Literal,
)
import numpy as np

_C = TypeVar("_C", bound=type)

if TYPE_CHECKING:
    _F = TypeVar("_F", bound=Callable)

    @overload
    def lru_cache(maxsize: int = 128, typed: bool = False) -> Callable[[_F], _F]: ...
    @overload
    def lru_cache(f: _F) -> _F: ...
else:
    from functools import lru_cache  # noqa: F401


def iter_subclasses(cls: _C) -> Iterator[_C]:
    """Recursively iterate over all subclasses of a class."""
    for sub in cls.__subclasses__():
        yield sub
        yield from iter_subclasses(sub)


def is_structured(arr: np.ndarray) -> bool:
    """True if the array is structured."""
    return isinstance(arr.dtype, (np.void, np.dtypes.VoidDType))


_ANSI_BASIC = {
    1: {"font_weight": "bold"},
    2: {"font_weight": "lighter"},
    3: {"font_weight": "italic"},
    4: {"text_decoration": "underline"},
    5: {"text_decoration": "blink"},
    6: {"text_decoration": "blink"},
    8: {"visibility": "hidden"},
    9: {"text_decoration": "line-through"},
}

ANSI_STYLES_LIGHT = {
    **_ANSI_BASIC,
    30: {"color": "white"},
    31: {"color": "red"},
    32: {"color": "green"},
    33: {"color": "teal"},
    34: {"color": "blue"},
    35: {"color": "magenta"},
    36: {"color": "darkblue"},
    37: {"color": "black"},
}

ANSI_STYLES_DARK = {
    **_ANSI_BASIC,
    30: {"color": "black"},
    31: {"color": "orange"},
    32: {"color": "#a0ffae"},
    33: {"color": "yellow"},
    34: {"color": "#8e9dff"},
    35: {"color": "magenta"},
    36: {"color": "cyan"},
    37: {"color": "white"},
}


def ansi2html(
    ansi_string: str,
    is_dark: bool = False,
) -> Iterator[str]:
    """Convert ansi string to colored HTML

    Parameters
    ----------
    ansi_string : str
        text with ANSI color codes.
    styles : dict, optional
        A mapping from ANSI codes to a dict of css kwargs:values,
        by default ANSI_STYLES

    Yields
    ------
    str
        HTML strings that can be joined to form the final html
    """
    previous_end = 0
    styles = ANSI_STYLES_DARK if is_dark else ANSI_STYLES_LIGHT
    in_span = False
    ansi_codes = []
    ansi_finder = re.compile("\033\\[([\\d;]*)([a-zA-Z])")
    for match in ansi_finder.finditer(ansi_string):
        yield ansi_string[previous_end : match.start()]
        previous_end = match.end()
        params, command = match.groups()

        if command not in "mM":
            continue

        try:
            params = [int(p) for p in params.split(";")]
        except ValueError:
            params = [0]

        for i, v in enumerate(params):
            if v == 0:
                params = params[i + 1 :]
                if in_span:
                    in_span = False
                    yield "</span>"
                ansi_codes = []
                if not params:
                    continue

        ansi_codes.extend(params)
        if in_span:
            yield "</span>"
            in_span = False

        if not ansi_codes:
            continue

        style = [
            "; ".join([f"{k}: {v}" for k, v in styles[k].items()]).strip()
            for k in ansi_codes
            if k in styles
        ]
        yield '<span style="{}">'.format("; ".join(style))

        in_span = True

    yield ansi_string[previous_end:]
    if in_span:
        yield "</span>"
        in_span = False


class PluginInfo(NamedTuple):
    """Tuple that describes a plugin function."""

    module: str
    name: str

    def to_str(self) -> str:
        """Return the string representation of the plugin."""
        return f"{self.module}.{self.name}"

    @classmethod
    def from_str(cls, s: str) -> PluginInfo:
        """Create a PluginInfo from a string."""
        mod_name, func_name = s.rsplit(".", 1)
        return PluginInfo(module=mod_name, name=func_name)


def is_subtype(string: str, supertype: str) -> bool:
    """Check if the type is a subtype of the given type.

    ``` python
    is_subtype_of("text", "text")  # True
    is_subtype_of("text.plain", "text")  # True
    is_subtype_of("text.plain", "text.html")  # False
    ```
    """
    string_parts = string.split(".")
    supertype_parts = supertype.split(".")
    if len(supertype_parts) > len(string_parts):
        return False
    return string_parts[: len(supertype_parts)] == supertype_parts


def table_to_text(
    data: np.ndarray,
    format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
    end_of_text: Literal["", "\n"] = "\n",
) -> tuple[str, str, str]:
    from tabulate import tabulate

    format = format.lower()
    if format == "markdown":
        s = tabulate(data[1:], headers=data[0], tablefmt="github")
        ext_default = ".md"
        language = "markdown"
    elif format == "latex":
        s = _table_to_latex(data)
        ext_default = ".tex"
        language = "latex"
    elif format == "html":
        s = tabulate(data, tablefmt="html")
        ext_default = ".html"
        language = "html"
    elif format == "rst":
        s = tabulate(data, tablefmt="rst")
        ext_default = ".rst"
        language = "rst"
    elif format == "csv":
        s = _to_csv_like(data, ",")
        ext_default = ".csv"
        language = None
    elif format == "tsv":
        s = _to_csv_like(data, "\t")
        ext_default = ".tsv"
        language = None
    else:
        raise ValueError(f"Unknown format: {format}")
    return s + end_of_text, ext_default, language


def _to_csv_like(data: np.ndarray, sep: str) -> str:
    """Convert a table to CSV-like string."""
    return "\n".join(sep.join(str(r) for r in row) for row in data)


def _table_to_latex(table: np.ndarray) -> str:
    """Convert a table to LaTeX."""
    header = table[0]
    body = table[1:]
    latex = "\\begin{tabular}{" + "c" * len(header) + "}\n"
    latex += " & ".join(header) + " \\\\\n"
    for row in body:
        latex += " & ".join(str(r) for r in row) + " \\\\\n"
    latex += "\\hline\n"
    latex += "\\end{tabular}"
    return latex
