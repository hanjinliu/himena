from __future__ import annotations
from pathlib import Path
import weakref
from qtpy import QtWidgets as QtW, QtCore
from royalapp.widgets import MainWindow
from royalapp.io import get_readers


class QFileSystemModel(QtW.QFileSystemModel):
    def columnCount(self, parent) -> int:
        return 1


class QWorkspaceFileTree(QtW.QTreeView):
    def __init__(self, ui: MainWindow) -> None:
        super().__init__()
        self._model = QFileSystemModel(self)
        self.setModel(self._model)
        self.setHeaderHidden(True)
        self.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self._model.setRootPath(str(Path.cwd()))
        self._main_window_ref = weakref.ref(ui)
        self.doubleClicked.connect(self._double_clicked)

    def _double_clicked(self, index: QtCore.QModelIndex):
        idx = self._model.index(index.row(), 0, index.parent())
        path = Path(self._model.filePath(idx))
        if path.is_dir():
            return
        readers = get_readers(path)
        model = readers[0](path)
        self._main_window_ref().add_data_model(model)
        return None
