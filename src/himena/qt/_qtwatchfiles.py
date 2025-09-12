from __future__ import annotations

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
        if self._subwindow.is_alive:
            self._subwindow.update_model(model)

    def _on_target_window_closed(self):
        self._watcher.removePaths([str(self._file_path)])
        self._watcher.fileChanged.disconnect(self._on_file_change)
        self._instances.discard(self)
        self._subwindow._save_behavior = self._old_save_behavior
        self._subwindow.closed.disconnect(self._on_target_window_closed)
