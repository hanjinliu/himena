from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from app_model.types import Action
from royalapp.consts import MenuId

if TYPE_CHECKING:
    from royalapp.widgets._main_window import MainWindow


class OpenRecentFunction:
    def __init__(self, file: Path | list[Path]):
        self._file = file

    def __call__(self, ui: MainWindow):
        ui.read_file(self._file)


def action_for_file(file: Path | list[Path]) -> Action:
    if isinstance(file, Path):
        id = f"open-{file}"
        title = str(file)
    else:
        name = ";".join([f.name for f in file])
        id = f"open-{name}"
        title = f"{len(file)} files such as {file[0]}"

    return Action(
        id=id,
        title=title,
        callback=OpenRecentFunction(file),
        menus=[MenuId.FILE_RECENT],
    )
