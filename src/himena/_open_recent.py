from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from app_model.types import Action
from logging import getLogger
import json
from himena.consts import MenuId, ActionCategory, ActionGroup, NO_RECORDING_FIELD
from himena.profile import data_dir
from datetime import datetime

if TYPE_CHECKING:
    from app_model import Application
    from himena.widgets._main_window import MainWindow

    _PathInput = Path | list[Path]

_LOGGER = getLogger(__name__)


class OpenRecentFunction:
    def __init__(self, file: _PathInput, plugin: str | None = None):
        self._file = file
        self._plugin = plugin
        setattr(self, NO_RECORDING_FIELD, True)  # don't record "open" command

    def __call__(self, ui: MainWindow):
        _LOGGER.debug("Calling OpenRecentFunction for %s", self._file)
        ui.read_file(self._file, plugin=self._plugin)

    def to_str(self) -> str:
        return f"Open {self._file.as_posix()}"


class OpenSessionFunction:
    def __init__(self, file: _PathInput):
        self._file = file

    def __call__(self, ui: MainWindow):
        ui.read_session(self._file)

    def to_str(self) -> str:
        return f"Load session {self._file.as_posix()}"


class RecentFileManager:
    def __init__(
        self,
        app: Application,
        menu_id: MenuId = MenuId.FILE_RECENT,
        file_name: str = "recent.json",
        group: str = ActionGroup.RECENT_FILE,
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
        file_args = self._list_args_for_recent()[::-1]
        if len(file_args) == 0:
            return None
        actions = [
            self.action_for_file(path, plugin, in_menu=i < self._n_history_menu)
            for i, (path, plugin) in enumerate(file_args)
        ]
        self._disposer()
        self._disposer = self._app.register_actions(actions)
        _LOGGER.debug("Recent files updated: %r", [p.name for p, _ in file_args])
        self._app.menus.menus_changed.emit({self._menu_id})
        return None

    @classmethod
    def default(cls, app: Application) -> RecentFileManager:
        return cls(app)

    def _list_args_for_recent(self) -> list[tuple[_PathInput, str | None]]:
        """List the recent files (older first)."""

        _path = data_dir() / self._file_name
        if not _path.exists():
            return []
        with open(_path) as f:
            js = json.load(f)
        if not isinstance(js, list):
            return []
        out: list[tuple[_PathInput, str | None]] = []
        for each in js:
            if not isinstance(each, dict):
                continue
            if "type" not in each:
                continue
            if each["type"] == "group":
                out.append(([Path(p) for p in each["path"]], each.get("plugin")))
            elif each["type"] == "file":
                out.append((Path(each["path"]), each.get("plugin")))
        return out

    def append_recent_files(
        self,
        inputs: list[tuple[_PathInput, str | None]],
    ) -> None:
        """Append file(s) with plugin to the user history."""
        _path = data_dir() / self._file_name
        if _path.exists():
            with open(_path) as f:
                all_info = json.load(f)
            if not isinstance(all_info, list):
                all_info = []
        else:
            all_info = []
        existing_paths = [each["path"] for each in all_info]
        to_remove: list[int] = []
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        for each_path_input, plugin in inputs:
            each = _norm_path_input(each_path_input)
            if each in existing_paths:
                to_remove.append(existing_paths.index(each))
            if isinstance(each, list):
                all_info.append(
                    {"type": "group", "path": each, "plugin": plugin, "time": now}
                )
            elif Path(each).is_file():
                all_info.append(
                    {"type": "file", "path": each, "plugin": plugin, "time": now}
                )
            else:
                all_info.append(
                    {"type": "folder", "path": each, "plugin": plugin, "time": now}
                )
        for i in sorted(to_remove, reverse=True):
            all_info.pop(i)
        if len(all_info) > self._n_history:
            all_info = all_info[-self._n_history :]
        with open(_path, "w") as f:
            json.dump(all_info, f, indent=2)
        self.update_menu()
        return None

    def action_for_file(
        self,
        file: _PathInput,
        plugin: str | None = None,
        in_menu: bool = True,
    ) -> Action:
        """Make an Action for opening a file."""
        id, title = self.id_title_for_file(file)
        if in_menu:
            menus = [
                {"id": MenuId.RECENT_ALL},
                {"id": self._menu_id, "group": self._group},
            ]
        else:
            menus = [{"id": MenuId.RECENT_ALL}]
        return Action(
            id=id,
            title=title,
            callback=self.to_callback(file, plugin),
            menus=menus,
            category=ActionCategory.OPEN_RECENT,
            palette=False,
        )

    def to_callback(self, file, plugin: str | None = None):
        return OpenRecentFunction(file, plugin)

    def id_title_for_file(self, file: _PathInput) -> tuple[str, str]:
        """Return ID and title for the file."""
        if isinstance(file, Path):
            title = _title_for_file(file)
            id = f"open-{title}"
        else:
            name = ";".join([f.name for f in file])
            id = f"open-{name}"
            title = f"{len(file)} files such as {file[0]}"
        return id, title


class RecentSessionManager(RecentFileManager):
    @classmethod
    def default(cls, app: Application) -> RecentSessionManager:
        return cls(
            app,
            file_name="recent_sessions.json",
            group=ActionGroup.RECENT_SESSION,
            n_history=20,
            n_history_menu=3,
        )

    def to_callback(self, file, plugin: str | None = None):
        return OpenSessionFunction(file)

    def id_title_for_file(self, file: Path) -> tuple[str, str]:
        """Return the ID for the file."""
        fp = _title_for_file(file)
        id = f"load-session-{fp}"
        title = f"{fp} [Session]"
        return id, title


def _norm_path_input(each: _PathInput) -> str | list[str]:
    if isinstance(each, list):
        return [p.as_posix() for p in each]
    else:
        return each.as_posix()


def _title_for_file(file: Path) -> str:
    home = Path.home()
    if file.is_relative_to(home):
        title = ("~" / file.relative_to(home)).as_posix()
    else:
        title = file.as_posix()
    return title
