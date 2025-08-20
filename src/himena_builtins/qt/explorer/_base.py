from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile
from typing import TYPE_CHECKING, Literal
from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt.utils import thread_worker

from himena import _drag
from himena.qt._qsvg import QColoredSVGIcon
from himena.types import WidgetDataModel, DragDataModel
from himena.workflow import PathReaderMethod
from himena.consts import MonospaceFontFamily
from himena.plugins import validate_protocol
from himena.widgets import notify, set_status_tip
from himena.style import Theme
from himena_builtins._consts import ICON_PATH

if TYPE_CHECKING:
    from himena.qt import MainWindowQt


class QBaseRemoteExplorerWidget(QtW.QWidget):
    themeChanged = QtCore.Signal(Theme)

    def __init__(self, ui: MainWindowQt):
        super().__init__()

        self.setAcceptDrops(True)

        self._pwd = Path("~")
        self._last_dir = self._pwd
        self._ui = ui
        font = QtGui.QFont(MonospaceFontFamily)

        self._pwd_widget = QtW.QLineEdit()
        self._pwd_widget.setFont(font)
        self._pwd_widget.editingFinished.connect(self._on_pwd_edited)

        self._file_list_widget = QRemoteTreeWidget(self)
        self._file_list_widget.itemActivated.connect(self._read_item_to_gui)
        self._file_list_widget.setFont(font)
        self._file_list_widget.item_copied.connect(self._copy_item_paths)
        self._file_list_widget.item_pasted.connect(self._send_files)

        self._filter_widget = QFilterLineEdit(self)
        self._filter_widget.textChanged.connect(self._file_list_widget._apply_filter)
        self._filter_widget.setVisible(False)

    def _make_mimedata_for_items(
        self,
        items: list[QtW.QTreeWidgetItem],
    ) -> QtCore.QMimeData:
        mime = QtCore.QMimeData()
        mime.setText(
            "\n".join(
                meth.to_str() for meth in self._make_reader_methods_for_items(items)
            )
        )
        mime.setHtml(
            "<br>".join(
                f'<span ftype="{"d" if meth.force_directory else "f"}">{meth.to_str()}</span>'
                for meth in self._make_reader_methods_for_items(items)
            )
        )
        mime.setParent(self)  # this is needed to trace where the MIME data comes from
        return mime

    def _make_reader_methods_for_items(
        self, items: list[QtW.QTreeWidgetItem]
    ) -> list[PathReaderMethod]:
        methods: list[PathReaderMethod] = []
        for item in items:
            typ = item_type(item)
            if typ == "l":
                _, real_path = item.text(0).split(" -> ")
                remote_path = self._pwd / real_path
                is_dir = False
            else:
                remote_path = self._pwd / item.text(0)
                is_dir = typ == "d"
            meth = self._make_reader_method(remote_path, is_dir)
            methods.append(meth)
        return methods

    @thread_worker
    def _read_remote_path_worker(
        self, path: Path, is_dir: bool = False
    ) -> WidgetDataModel:
        return self._make_reader_method(path, is_dir).run()

    def _read_and_add_model(self, path: Path, is_dir: bool = False):
        """Read the remote file in another thread and add the model in the main."""
        worker = self._read_remote_path_worker(path, is_dir)
        worker.returned.connect(self._ui.add_data_model)
        worker.started.connect(lambda: self._set_busy(True))
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()
        set_status_tip(f"Reading file: {path}", duration=2.0)

    def _set_busy(self, busy: bool):
        pass  # This method can be overridden to set a busy state in the UI

    #############################################
    #### Need to be overridden in subclasses ####
    #############################################
    def _make_reader_method(self, path: Path, is_dir: bool) -> PathReaderMethod:
        raise NotImplementedError

    def _set_current_path(self, path: Path):
        """Set the current path and update the UI accordingly."""

    def _make_ls_args(self, path: str) -> list[str]:
        raise NotImplementedError

    def _make_get_type_args(self, path: str) -> list[str]:
        """Make the command to get the type of a file."""
        raise NotImplementedError

    def _make_local_to_remote_args(
        self, src: Path, dst_remote: str, is_dir: bool = False
    ) -> list[str]:
        """Make the command to send a local file to the remote host."""
        raise NotImplementedError

    def readers_from_mime(self, mime: QtCore.QMimeData) -> list[PathReaderMethod]:
        """Construct readers from the mime data."""
        raise NotImplementedError

    #############################################
    #############################################

    @thread_worker
    def _run_ls_command(self, path: Path) -> list[QtW.QTreeWidgetItem]:
        args = self._make_ls_args(path.as_posix())
        result = subprocess.run(args, capture_output=True)
        if result.returncode != 0:
            raise ValueError(f"Failed to list directory: {result.stderr.decode()}")
        rows = result.stdout.decode().splitlines()
        # format of `ls -l` is:
        # <permission> <link> <owner> <group> <size> <month> <day> <time> <name>
        items: list[QtW.QTreeWidgetItem] = []
        for row in rows[1:]:  # the first line is total size
            *others, month, day, time, name = row.split(maxsplit=8)
            datetime = f"{month} {day} {time}"
            if name.endswith("*"):
                name = name[:-1]  # executable
            item = QtW.QTreeWidgetItem([name, datetime] + others[::-1])
            item.setToolTip(0, name)
            items.append(item)

        # sort directories first
        items = sorted(
            items,
            key=lambda x: (not x.text(0).endswith("/"), x.text(0)),
        )
        self._last_dir = self._pwd
        self._pwd = path
        return items

    def _read_item_to_gui(self, item: QtW.QTreeWidgetItem):
        typ = item_type(item)
        if typ == "d":
            self._set_current_path(self._pwd / item.text(0))
        elif typ == "l":
            _, real_path = item.text(0).split(" -> ")
            # solve relative path
            if real_path.startswith("../"):
                real_path_abs = self._pwd.parent.joinpath(real_path[3:])
            elif real_path.startswith("./"):
                real_path_abs = self._pwd.joinpath(real_path[2:])
            elif real_path.startswith(("/", "~")):
                real_path_abs = Path(real_path)
            else:
                real_path_abs = self._pwd / real_path
            args_check_type = self._make_get_type_args(real_path_abs.as_posix())
            result = subprocess.run(args_check_type, capture_output=True)
            if result.returncode != 0:
                raise ValueError(f"Failed to get type: {result.stderr.decode()}")

            link_type = result.stdout.decode().strip()
            if link_type == "directory":
                self._set_current_path(real_path_abs)
            else:
                self._read_and_add_model(real_path_abs)
        else:
            self._read_and_add_model(self._pwd / item.text(0))

    def _send_model(self, model: DragDataModel):
        data_model = model.data_model()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            src_pathobj = data_model.write_to_directory(tmpdir)
            self._send_file(src_pathobj)

    def _send_file(self, src: Path, is_dir: bool = False):
        """Send local file to the remote host."""
        dst_remote = self._pwd / src.name
        args = self._make_local_to_remote_args(
            src, dst_remote.as_posix(), is_dir=is_dir
        )
        subprocess.run(args)
        notify(f"Sent {src.as_posix()} to {dst_remote.as_posix()}", duration=2.8)

    def dragEnterEvent(self, a0):
        if _drag.get_dragging_model() is not None or a0.mimeData().urls():
            a0.accept()
        else:
            a0.ignore()

    def dragMoveEvent(self, a0):
        a0.acceptProposedAction()
        return super().dragMoveEvent(a0)

    def dropEvent(self, a0):
        if model := _drag.drop():
            self._ui.submit_async_task(self._send_model, model)
            set_status_tip("Start sending file ...")
        elif urls := a0.mimeData().urls():
            for url in urls:
                path = Path(url.toLocalFile())
                self._ui.submit_async_task(self._send_file, path, path.is_dir())
                set_status_tip(f"Sent to {path.name}", duration=2.8)

    def _copy_item_paths(self, items: list[QtW.QTreeWidgetItem]):
        mime = self._make_mimedata_for_items(items)
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setMimeData(mime)

    def _send_files(self, paths: list[Path]):
        for path in paths:
            self._ui.submit_async_task(self._send_file, path, path.is_dir())

    # widget methods
    @validate_protocol
    def theme_changed_callback(self, theme: Theme) -> None:
        self._light_background = theme.is_light_background()
        count = self._file_list_widget.topLevelItemCount()
        self._on_ls_done([self._file_list_widget.topLevelItem(i) for i in range(count)])
        self.themeChanged.emit(theme)

    def _set_current_path(self, path: Path):
        self._pwd_widget.setText(path.as_posix())
        self._file_list_widget.clear()
        worker = self._run_ls_command(path)
        worker.returned.connect(self._on_ls_done)
        worker.started.connect(lambda: self._set_busy(True))
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()
        set_status_tip("Obtaining the file content ...", duration=3.0)

    def _on_ls_done(self, items: list[QtW.QTreeWidgetItem]):
        for item in items:
            icon = icon_for_file_type(item_type(item), self._light_background)
            item.setIcon(0, icon)
        self._file_list_widget.addTopLevelItems(items)
        for i in range(1, self._file_list_widget.columnCount()):
            self._file_list_widget.resizeColumnToContents(i)
        set_status_tip(f"Currently under {self._pwd.name}", duration=1.0)

    def _on_pwd_edited(self):
        pwd_text = self._pwd_widget.text()
        if "*" in pwd_text or "?" in pwd_text:
            self._pwd_widget.setSelection(0, len(pwd_text))
            raise ValueError("Wildcards are not supported.")
        if self._pwd != Path(pwd_text):
            self._set_current_path(Path(pwd_text))

    def keyPressEvent(self, a0):
        if (
            a0.key() == QtCore.Qt.Key.Key_F
            and a0.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self._filter_widget.toggle()
            return
        return super().keyPressEvent(a0)


class QRemoteTreeWidget(QtW.QTreeWidget):
    item_copied = QtCore.Signal(list)
    item_pasted = QtCore.Signal(list)  # list of local Path objects

    def __init__(self, parent: QBaseRemoteExplorerWidget):
        super().__init__(parent)
        self.setIndentation(0)
        self.setColumnWidth(0, 180)
        self.setHeaderLabels(
            ["Name", "Datetime", "Size", "Group", "Owner", "Link", "Permission"]
        )
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.header().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.header().setFixedHeight(20)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        open_action = menu.addAction("Open")
        open_action.triggered.connect(
            lambda: self.itemActivated.emit(self.currentItem(), 0)
        )
        copy_action = menu.addAction("Copy Path")
        copy_action.triggered.connect(
            lambda: self.item_copied.emit(self.selectedItems())
        )
        paste_action = menu.addAction("Paste")
        paste_action.triggered.connect(self._paste_from_clipboard)
        menu.addSeparator()
        download_action = menu.addAction("Download")
        download_action.triggered.connect(
            lambda: self._save_items(self.selectedItems())
        )
        return menu

    def _show_context_menu(self, pos: QtCore.QPoint):
        self._make_context_menu().exec(self.viewport().mapToGlobal(pos))

    def keyPressEvent(self, event):
        _mod = event.modifiers()
        _key = event.key()
        if _mod == QtCore.Qt.KeyboardModifier.ControlModifier:
            if _key == QtCore.Qt.Key.Key_C:
                items = self.selectedItems()
                self.item_copied.emit(items)
                return None
            elif _key == QtCore.Qt.Key.Key_V:
                return self._paste_from_clipboard()
        return super().keyPressEvent(event)

    def _paste_from_clipboard(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            paths = [Path(url.toLocalFile()) for url in urls]
            self.item_pasted.emit(paths)
        else:
            notify("No valid file paths in the clipboard.")

    # drag-and-drop
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._start_drag(e.pos())
            return None
        return super().mouseMoveEvent(e)

    def _start_drag(self, pos: QtCore.QPoint):
        items = self.selectedItems()
        mime = self.parent()._make_mimedata_for_items(items)
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.DropAction.CopyAction)

    def _save_items(self, items: list[QtW.QTreeWidgetItem]):
        """Save the selected items to local files."""
        download_dir = Path.home() / "Downloads"
        src_paths: list[Path] = []
        for item in items:
            typ = item_type(item)
            if typ == "l":
                _, real_path = item.text(0).split(" -> ")
                remote_path = self.parent()._pwd / real_path
            else:
                remote_path = self.parent()._pwd / item.text(0)
            src_paths.append(remote_path)

        readers = self.parent()._make_reader_methods_for_items(items)
        worker = make_paste_remote_files_worker(readers, download_dir)
        qui = self.parent()._ui._backend_main_window
        qui._job_stack.add_worker(worker, "Downloading files", total=len(src_paths))
        worker.start()

    def _apply_filter(self, text: str):
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            ok = all(part in item.text(0).lower() for part in text.lower().split(" "))
            item.setHidden(not ok)

    if TYPE_CHECKING:

        def parent(self) -> QBaseRemoteExplorerWidget: ...


class QFilterLineEdit(QtW.QLineEdit):
    """Line edit for filtering items in the remote explorer."""

    def __init__(self, parent: QBaseRemoteExplorerWidget):
        super().__init__(parent)
        self.setPlaceholderText("Filter files...")

    def keyPressEvent(self, a0):
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.clear()
            self.setVisible(False)
            return
        return super().keyPressEvent(a0)

    def toggle(self):
        visible = self.isVisible()
        self.setVisible(not visible)
        if not visible:
            self.setFocus()


def item_type(item: QtW.QTreeWidgetItem) -> Literal["d", "l", "f"]:
    """First character of the permission string."""
    return item.text(6)[0]


@lru_cache(maxsize=10)
def icon_for_file_type(file_type: str, light_background: bool) -> QColoredSVGIcon:
    color = "#222222" if light_background else "#eeeeee"
    if file_type == "d":
        svg_path = ICON_PATH / "explorer_folder.svg"
    elif file_type == "l":
        svg_path = ICON_PATH / "explorer_symlink.svg"
    else:
        svg_path = ICON_PATH / "explorer_file.svg"
    return QColoredSVGIcon.fromfile(svg_path, color=color)


@thread_worker
def make_paste_remote_files_worker(
    readers: list[PathReaderMethod],
    dirpath: Path,
):
    for reader in readers:
        if isinstance(reader.path, Path):
            paths = [reader.path]
        else:
            paths = reader.path
        for path in paths:
            stem = path.stem
            ext = path.suffix
            suffix = 0
            dst = dirpath / f"{stem}{ext}"
            while dst.exists():
                dst = dirpath / f"{stem}_{suffix}{ext}"
                suffix += 1
            reader.run_command(dst)
            if dst.exists():
                dst.touch()
            yield
