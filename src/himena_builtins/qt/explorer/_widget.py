from __future__ import annotations
from pathlib import Path
import warnings
import shutil
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena import _drag
from himena.widgets import MainWindow
from himena_builtins.qt.explorer._widget_ssh import QSSHRemoteExplorerWidget

if TYPE_CHECKING:
    from himena_builtins.qt.explorer import FileExplorerConfig


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

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        # NOTE: renaming of item triggers renaming of the file by default.
        return super().flags(index) | QtCore.Qt.ItemFlag.ItemIsEditable


class QRootPathEdit(QtW.QWidget):
    """Widget to specify the root path of the file explorer."""

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
        self.set_root_path(path)

    def set_root_path(self, path: str | Path):
        path = Path(path)
        self._path_edit.setText("/" + path.name)
        self.rootChanged.emit(path)
        self._path_edit.setToolTip(path.as_posix())


class QExplorerWidget(QtW.QWidget):
    """A normal file explorer widget."""

    open_file_requested = QtCore.Signal(Path)

    def __init__(self, ui: MainWindow) -> None:
        super().__init__()
        self._ui = ui
        self._root = QRootPathEdit()
        self._file_tree = QFileTree(ui)
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(self._root)
        layout.addWidget(self._file_tree)
        self._root.set_root_path(Path.cwd())
        self._root.rootChanged.connect(self._file_tree.setRootPath)
        self._file_tree.fileDoubleClicked.connect(self.open_file_requested.emit)
        self.open_file_requested.connect(ui.read_file)

    def update_configs(self, cfg: FileExplorerConfig):
        self._file_tree._config = cfg


class QFileTree(QtW.QTreeView):
    fileDoubleClicked = QtCore.Signal(Path)

    def __init__(self, ui: MainWindow) -> None:
        from himena_builtins.qt.explorer import FileExplorerConfig

        super().__init__()
        self._ui = ui
        self._model = QFileSystemModel()
        self.setHeaderHidden(True)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.EditKeyPressed)
        self.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.setModel(self._model)
        self.setRootIndex(self._model.index(self._model.rootPath()))
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.doubleClicked.connect(self._double_clicked)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setAcceptDrops(True)
        self._config = FileExplorerConfig()

    def setRootPath(self, path: Path):
        path = Path(path)
        self._model.setRootPath(path.as_posix())
        self.setRootIndex(self._model.index(path.as_posix()))

    def _show_context_menu(self, pos: QtCore.QPoint):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        menu = QtW.QMenu(self)
        path = Path(self._model.filePath(index))
        menu.addAction("Open", lambda: self._ui.read_file(path))
        menu.addSeparator()
        menu.addAction("Copy", lambda: self._ui.set_clipboard(files=[path]))
        menu.addAction("Copy path", lambda: self._ui.set_clipboard(text=str(path)))
        menu.addAction("Paste", self._paste_from_clipboard)
        menu.addSeparator()
        menu.addAction("Rename", lambda: self.edit(index))
        menu.exec(self.viewport().mapToGlobal(pos))
        return None

    def _double_clicked(self, index: QtCore.QModelIndex):
        idx = self._model.index(index.row(), 0, index.parent())
        path = Path(self._model.filePath(idx))
        if path.is_dir():
            return
        self.fileDoubleClicked.emit(path)
        return None

    # drag-and-drop
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._start_drag(e.pos())
            return None
        return super().mouseMoveEvent(e)

    def _start_drag(self, pos: QtCore.QPoint):
        mime = QtCore.QMimeData()
        selected_indices = self.selectedIndexes()
        urls = [self._model.filePath(idx) for idx in selected_indices]
        mime.setUrls([QtCore.QUrl.fromLocalFile(url) for url in urls])
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        if (nfiles := len(selected_indices)) == 1:
            pixmap = self._model.fileIcon(selected_indices[0]).pixmap(10, 10)
        else:
            qlabel = QtW.QLabel(f"{nfiles} files")
            pixmap = QtGui.QPixmap(qlabel.size())
            qlabel.render(pixmap)
        drag.setPixmap(pixmap)
        cursor = QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        drag.setDragCursor(cursor.pixmap(), QtCore.Qt.DropAction.MoveAction)
        drag.exec(QtCore.Qt.DropAction.MoveAction)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent):
        mime = a0.mimeData()
        if mime and (
            mime.hasUrls() or isinstance(mime.parent(), QSSHRemoteExplorerWidget)
        ):
            a0.accept()
        elif _drag.get_dragging_model() is not None:
            a0.accept()
        else:
            a0.ignore()
        return None

    def dragMoveEvent(self, a0: QtGui.QDragMoveEvent):
        mime = a0.mimeData()
        if mime and (
            mime.hasUrls() or isinstance(mime.parent(), QSSHRemoteExplorerWidget)
        ):
            a0.accept()
        elif _drag.get_dragging_model() is not None:
            a0.accept()
        else:
            a0.ignore()
            return
        index = self._get_directory_index(self.indexAt(a0.pos()))
        self.selectionModel().setCurrentIndex(
            index, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        a0.acceptProposedAction()
        return None

    def dropEvent(self, a0: QtGui.QDropEvent):
        dirpath = self._directory_for_index(self.indexAt(a0.pos()))
        if drag_model := _drag.drop():
            if self._config.allow_drop_data_to_save:
                data_model = drag_model.data_model()
                data_model.write_to_directory(dirpath)
        elif mime := a0.mimeData():
            self._paste_mime_data(mime, dirpath)

    def dragLeaveEvent(self, e):
        return super().dragLeaveEvent(e)

    def keyPressEvent(self, event):
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.key() == QtCore.Qt.Key.Key_C:
                self._ui.set_clipboard(
                    files=[
                        Path(self._model.filePath(idx))
                        for idx in self.selectedIndexes()
                    ]
                )
                return
            elif event.key() == QtCore.Qt.Key.Key_V:
                return self._paste_from_clipboard()
        return super().keyPressEvent(event)

    def _paste_from_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            dirpath = self._directory_for_index(self.currentIndex())
            self._paste_mime_data(clipboard.mimeData(), dirpath)

    def _paste_mime_data(self, mime: QtCore.QMimeData, dirpath: Path):
        if isinstance(par := mime.parent(), QSSHRemoteExplorerWidget):
            for reader in par.readers_from_text(mime.text()):
                reader.run_scp(dirpath)
        else:
            self._paste_file(
                self._ui.clipboard.files,
                dirpath=dirpath,
                is_copy=True,
            )

    def _paste_file(self, paths: list[Path], dirpath: Path, is_copy: bool):
        dst_exists: list[Path] = []
        src_dst_set: list[tuple[Path, Path]] = []
        for src in paths:
            if not src.exists():
                warnings.warn(f"Path {src} does not exist.", stacklevel=2)
                continue
            dst = dirpath / src.name
            if src != dst:
                if dst.exists():
                    dst_exists.append(dst)
                src_dst_set.append((src, dst))
        if src_dst_set and self._config.allow_drop_file_to_move:
            if dst_exists:
                conflicts = "\n - ".join(p.name for p in dst_exists)
                answer = self._ui.exec_choose_one_dialog(
                    "Replace existing files?",
                    f"Name conflict in the destinations:\n{conflicts}",
                    ["Replace", "Skip", "Cancel"],
                )
                if answer == "Cancel":
                    return
                elif answer == "Replace":
                    pass
                else:
                    src_dst_set = [
                        (src, dst) for src, dst in src_dst_set if dst not in dst_exists
                    ]
            for src, dst in src_dst_set:
                if is_copy:
                    shutil.copy(src, dst)
                else:
                    shutil.move(src, dst)

    def _get_directory_index(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return self.rootIndex()
        _is_directory = self.model().hasChildren(index)
        if _is_directory:
            return index
        else:
            return self.model().parent(index)

    def _directory_for_index(self, index: QtCore.QModelIndex) -> Path:
        dir_index = self._get_directory_index(index)
        if dirpath := self.model().filePath(dir_index):
            return Path(dirpath)
        else:
            raise ValueError(f"Invalid destination: {dirpath}")
