from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from qtpy import QtCore
from himena._descriptors import SaveToPath, CannotSave
from himena._providers import ReaderStore

if TYPE_CHECKING:
    from himena.widgets import SubWindow


class QWatchFileObject(QtCore.QObject):
    _instances = set()

    def __init__(self, win: SubWindow):
        super().__init__()
        if not isinstance(sb := win.save_behavior, SaveToPath):
            raise ValueError("no file to watch")
        if not win.supports_update_model:
            raise ValueError(f"Window {win.title!r} does not implement `update_model`.")
        self._subwindow = win
        self._old_save_behavior = sb
        self._file_path = sb.path
        self._watcher = QtCore.QFileSystemWatcher([str(sb.path)])

        win.closed.connect(self._on_target_window_closed)
        self._watcher.fileChanged.connect(self._on_file_change)
        win._save_behavior = CannotSave(reason="File watching is enabled")
        self.__class__._instances.add(self)

    def _on_file_change(self):
        ins = ReaderStore.instance()
        model = ins.run(self._file_path, plugin=self._old_save_behavior.plugin)
        self._subwindow.update_model(model)

    def _on_target_window_closed(self):
        self._watcher.removePaths([str(self._file_path)])
        self._watcher.fileChanged.disconnect(self._on_file_change)
        self._instances.discard(self)
        self._subwindow._save_behavior = self._old_save_behavior
        self._subwindow.closed.disconnect(self._on_target_window_closed)


class QWatchWindowObject(QtCore.QObject):
    _instances = set()

    def __init__(
        self,
        window_watch: SubWindow,
        window_update: SubWindow,
        interval_sec: float = 1.0,
    ):
        super().__init__()
        if not window_watch.supports_to_model:
            raise ValueError(
                f"Window {window_watch.title!r} does not implement `to_model`."
            )
        if not window_update.supports_update_model:
            raise ValueError(
                f"Window {window_update.title!r} does not implement `update_model`."
            )
        self._win_watch = window_watch
        self._win_update = window_update
        self._timer = QtCore.QTimer()
        self._timer.setInterval(int(interval_sec * 1000))
        self._timer.timeout.connect(self._elapsed)
        window_watch.closed.connect(self._on_target_window_closed)
        self.__class__._instances.add(self)
        self._was_editable = window_update.is_editable
        with suppress(AttributeError):
            window_update.is_editable = False

    def _elapsed(self):
        self._win_update.update_model(self._win_watch.to_model())

    def _on_target_window_closed(self):
        self._instances.discard(self)
        self._win_watch.closed.disconnect(self._on_target_window_closed)
        with suppress(AttributeError):
            self._win_update.is_editable = self._was_editable
        self._timer.stop()
