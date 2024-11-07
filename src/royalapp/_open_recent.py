from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from app_model.types import Action
import json
from royalapp.consts import MenuId, ActionCategory
from royalapp.profile import data_dir

if TYPE_CHECKING:
    from app_model import Application
    from royalapp.widgets._main_window import MainWindow


class OpenRecentFunction:
    def __init__(self, file: Path | list[Path]):
        self._file = file

    def __call__(self, ui: MainWindow):
        ui.read_file(self._file)

    def to_str(self) -> str:
        return f"Open {self._file.as_posix()}"


class OpeRecentManager:
    def __init__(
        self,
        app: Application,
        menu_id: MenuId = MenuId.FILE_RECENT,
        file_name: str = "recent.json",
        group: str = "00_recent_files",
        n_history: int = 60,
        n_history_menu: int = 8,
    ):
        self._disposer = lambda: None
        self._app = app
        self._menu_id = menu_id
        self._file_name = file_name
        self._group = group
        self._n_history = n_history
        self._n_history_menu = n_history_menu

    def update_menu(self):
        """Update the app name for the recent file list."""
        file_paths = self._list_recent_files()[::-1]
        if len(file_paths) == 0:
            return None
        actions = [
            self.action_for_file(path, in_menu=i < self._n_history_menu)
            for i, path in enumerate(file_paths)
        ]
        self._disposer()
        self._disposer = self._app.register_actions(actions)
        self._app.menus.menus_changed.emit({self._menu_id})
        return None

    @classmethod
    def default_recent_files(cls, app: Application) -> OpeRecentManager:
        return cls(app)

    @classmethod
    def default_recent_sessions(cls, app: Application) -> OpeRecentManager:
        return cls(
            app,
            file_name="recent_sessions.json",
            group="01_recent_sessions",
            n_history=20,
            n_history_menu=3,
        )

    def _list_recent_files(self) -> list[Path | list[Path]]:
        """List the recent files (older first)."""

        _path = data_dir() / self._file_name
        if not _path.exists():
            return []
        with open(_path) as f:
            js = json.load(f)
        if not isinstance(js, list):
            return []
        paths: list[Path | list[Path]] = []
        for each in js:
            if not isinstance(each, dict):
                continue
            if "type" not in each:
                continue
            if each["type"] == "group":
                paths.append([Path(p) for p in each["path"]])
            elif each["type"] == "file":
                path = Path(each["path"])
                paths.append(path)
        return paths

    def append_recent_files(self, inputs: list[Path | list[Path]]) -> None:
        _path = data_dir() / self._file_name
        inputs_str = _path_to_list(inputs)
        if _path.exists():
            with open(_path) as f:
                all_info = json.load(f)
            if not isinstance(all_info, list):
                all_info = []
        else:
            all_info = []
        existing_paths = [each["path"] for each in all_info]
        to_remove: list[int] = []
        for each in inputs_str:
            if each in existing_paths:
                to_remove.append(existing_paths.index(each))
            if isinstance(each, list):
                all_info.append({"type": "group", "path": each})
            elif Path(each).is_file():
                all_info.append({"type": "file", "path": each})
            else:
                all_info.append({"type": "folder", "path": each})
        for i in sorted(to_remove, reverse=True):
            all_info.pop(i)
        if len(all_info) > self._n_history:
            all_info = all_info[-self._n_history :]
        with open(_path, "w") as f:
            json.dump(all_info, f, indent=2)
        return None

    def action_for_file(
        self,
        file: Path | list[Path],
        in_menu: bool = True,
    ) -> Action:
        """Make an Action for opening a file."""
        if isinstance(file, Path):
            id = f"open-{file}"
            title = str(file)
        else:
            name = ";".join([f.name for f in file])
            id = f"open-{name}"
            title = f"{len(file)} files such as {file[0]}"

        if in_menu:
            menus = [{"id": self._menu_id, "group": self._group}]
        else:
            menus = []
        return Action(
            id=id,
            title=title,
            callback=OpenRecentFunction(file),
            menus=menus,
            category=ActionCategory.OPEN_RECENT,
            palette=False,
        )


def _path_to_list(obj: list[Path | list[Path]]) -> list[str | list[str]]:
    out = []
    for each in obj:
        if isinstance(each, list):
            out.append([p.as_posix() for p in each])
        else:
            out.append(each.as_posix())
    return out
