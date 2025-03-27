from __future__ import annotations

from typing import Iterator, overload
from pathlib import Path

from himena.widgets import MainWindow
from contextlib import contextmanager


@overload
@contextmanager
def file_dialog_response(
    ui: MainWindow,
    path: str | Path,
    *,
    confirm: bool = False,
) -> Iterator[Path]: ...


@overload
@contextmanager
def file_dialog_response(
    ui: MainWindow,
    path: list[str | Path],
    *,
    confirm: bool = False,
) -> Iterator[list[Path]]: ...


@contextmanager
def file_dialog_response(
    ui: MainWindow,
    path: str | Path | list[str | Path],
    *,
    confirm: bool = False,
):
    """Set the response of the file dialog in this context."""
    old_inst = ui._instructions
    if isinstance(path, list):
        path = [Path(p) for p in path]
    else:
        path = Path(path)
    try:
        ui._instructions = ui._instructions.updated(
            file_dialog_response=lambda: path,
            confirm=confirm,
        )
        yield path
    finally:
        ui._instructions = old_inst


@contextmanager
def choose_one_dialog_response(ui: MainWindow, choice: str):
    """Set the response of the choose one dialog in this context."""
    old_inst = ui._instructions
    try:
        ui._instructions = ui._instructions.updated(
            choose_one_dialog_response=lambda: choice
        )
        yield
    finally:
        ui._instructions = old_inst
