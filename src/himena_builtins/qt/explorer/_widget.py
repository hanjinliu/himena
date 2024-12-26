from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW, QtCore, QtGui


class QFileSystemModel(QtW.QFileSystemModel):
    def __init__(self):
        super().__init__()
        self.setRootPath(Path.cwd().as_posix())

    def columnCount(self, parent) -> int:
        return 1

    def data(self, index: QtCore.QModelIndex, role: int):
        if role == QtCore.Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(18, 16)
        return super().data(index, role)


class QRootPathEdit(QtW.QWidget):
    rootChanged = QtCore.Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._path_edit = QtW.QLabel()
        self._path_edit.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._btn_set_root = QtW.QPushButton("...")
        self._btn_set_root.setFixedWidth(20)
        self._btn_set_root.clicked.connect(self._select_root_path)
        layout.addWidget(self._path_edit)
        layout.addWidget(self._btn_set_root)

    def _select_root_path(self):
        path = QtW.QFileDialog.getExistingDirectory(self, "Select Root Path")
        if not path:
            return
        self._set_root_path(path)

    def _set_root_path(self, path: str | Path):
        path = Path(path)
        self._path_edit.setText("/" + path.name)
        self.rootChanged.emit(path)


class QExplorerWidget(QtW.QWidget):
    fileDoubleClicked = QtCore.Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self._root = QRootPathEdit()
        self._workspace_tree = QWorkspaceFileTree()
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(self._root)
        layout.addWidget(self._workspace_tree)
        self._root._path_edit.setText("/" + Path.cwd().name)
        self._root.rootChanged.connect(self._workspace_tree.setRootPath)
        self._workspace_tree.fileDoubleClicked.connect(self.fileDoubleClicked.emit)


class QWorkspaceFileTree(QtW.QTreeView):
    fileDoubleClicked = QtCore.Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self._model = QFileSystemModel()
        self.setHeaderHidden(True)
        self.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.setModel(self._model)
        self.setRootIndex(self._model.index(self._model.rootPath()))
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.doubleClicked.connect(self._double_clicked)

    def setRootPath(self, path: Path):
        path = Path(path)
        self._model.setRootPath(path.as_posix())
        self.setRootIndex(self._model.index(path.as_posix()))

    def _double_clicked(self, index: QtCore.QModelIndex):
        idx = self._model.index(index.row(), 0, index.parent())
        path = Path(self._model.filePath(idx))
        if path.is_dir():
            return
        self.fileDoubleClicked.emit(path)
        return None

    # drag-and-drop
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self._startDrag(e.pos())
        return super().mouseMoveEvent(e)

    def _startDrag(self, pos: QtCore.QPoint):
        mime = QtCore.QMimeData()
        selected_indices = self.selectedIndexes()
        urls = [self._model.filePath(idx) for idx in selected_indices]
        mime.setUrls([QtCore.QUrl.fromLocalFile(url) for url in urls])
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        cursor = QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        drag.setDragCursor(cursor.pixmap(), QtCore.Qt.DropAction.MoveAction)
        drag.exec(QtCore.Qt.DropAction.MoveAction)
