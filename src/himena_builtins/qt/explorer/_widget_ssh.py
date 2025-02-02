from __future__ import annotations

import sys
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt.utils import thread_worker

from himena.workflow import SCPReaderMethod
from himena import _drag
from himena.consts import MonospaceFontFamily
from himena.types import DragDataModel, WidgetDataModel
from himena.widgets import MainWindow, set_status_tip, notify
from himena.qt.magicgui._toggle_switch import QLabeledToggleSwitch
from himena_builtins.qt.widgets._shared import labeled

if TYPE_CHECKING:
    from himena_builtins.qt.explorer import FileExplorerSSHConfig


class QSSHRemoteExplorerWidget(QtW.QWidget):
    """A widget for exploring remote files via SSH.

    This widget will execute `ls`, `ssh` and `scp` commands to list, read and send
    files when needed. This widget accepts copy-and-paste drag-and-drop from the local
    file system, including the normal explorer dock widget and the OS file explorer.

    If you are using Windows, checking the "Use WSL" switch will forward all the
    subprocess commands to WSL.
    """

    on_ls = QtCore.Signal(object)

    def __init__(self, ui: MainWindow) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        font = QtGui.QFont(MonospaceFontFamily)
        self._ui = ui
        self._host_edit = QtW.QLineEdit()
        self._host_edit.setFont(font)
        self._host_edit.setMaximumWidth(140)
        self._user_name_edit = QtW.QLineEdit()
        self._user_name_edit.setFont(font)
        self._is_wsl_switch = QLabeledToggleSwitch()
        self._is_wsl_switch.setText("Use WSL")
        self._is_wsl_switch.setFixedHeight(24)
        self._is_wsl_switch.setChecked(False)
        self._is_wsl_switch.setVisible(sys.platform == "win32")
        self._is_wsl_switch.setToolTip(
            "Use WSL (Windows Subsystem for Linux) to access remote files. If \n "
            "checked, all the subprocess commands such as `scp` and `ls` will be \n"
            "prefixed with `wsl -e`."
        )

        self._show_hidden_files_switch = QLabeledToggleSwitch()
        self._show_hidden_files_switch.setText("Hidden Files")
        self._show_hidden_files_switch.setToolTip("Also show hidden files")
        self._show_hidden_files_switch.setFixedHeight(24)
        self._show_hidden_files_switch.setChecked(False)

        self._pwd_widget = QtW.QLineEdit()
        self._pwd_widget.setFont(font)
        self._pwd_widget.editingFinished.connect(self._on_pwd_edited)

        self._last_dir_btn = QtW.QPushButton("←")
        self._last_dir_btn.setFixedWidth(20)
        self._last_dir_btn.setToolTip("Back to last directory")

        self._up_one_btn = QtW.QPushButton("↑")
        self._up_one_btn.setFixedWidth(20)
        self._up_one_btn.setToolTip("Up one directory")
        self._refresh_btn = QtW.QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(60)
        self._refresh_btn.setToolTip("Refresh current directory")

        self._conn_btn = QtW.QPushButton("Connect")
        self._conn_btn.setFixedWidth(60)
        self._conn_btn.setToolTip("Connect to the remote host with the given user name")

        self._file_list_widget = QRemoteTreeWidget(self)
        self._file_list_widget.itemActivated.connect(self._read_item_to_gui)
        self._file_list_widget.setFont(font)
        self._file_list_widget.item_copied.connect(self._copy_item_paths)
        self._file_list_widget.item_pasted.connect(self._send_files)

        self._pwd = Path("~")
        self._last_dir = Path("~")

        layout = QtW.QVBoxLayout(self)

        hlayout0 = QtW.QHBoxLayout()
        hlayout0.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hlayout0)
        hlayout0.addWidget(labeled("Host:", self._host_edit, label_width=30), 3)
        hlayout0.addWidget(labeled("User:", self._user_name_edit, label_width=30), 2)

        hlayout1 = QtW.QHBoxLayout()
        hlayout1.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hlayout1)
        hlayout1.addWidget(self._is_wsl_switch)
        hlayout1.addWidget(self._conn_btn)

        layout.addWidget(QSeparator())
        layout.addWidget(labeled("Path:", self._pwd_widget))

        hlayout2 = QtW.QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.addWidget(self._last_dir_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hlayout2.addWidget(self._up_one_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hlayout2.addWidget(QtW.QWidget())
        hlayout2.addWidget(self._show_hidden_files_switch)
        hlayout2.addWidget(self._refresh_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addLayout(hlayout2)
        layout.addWidget(self._file_list_widget)

        self._conn_btn.clicked.connect(lambda: self._set_current_path(Path("~")))
        self._refresh_btn.clicked.connect(lambda: self._set_current_path(self._pwd))
        self._last_dir_btn.clicked.connect(
            lambda: self._set_current_path(self._last_dir)
        )
        self._up_one_btn.clicked.connect(
            lambda: self._set_current_path(self._pwd.parent)
        )
        self._show_hidden_files_switch.toggled.connect(
            lambda: self._set_current_path(self._pwd)
        )

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
        self._file_list_widget.addTopLevelItems(items)
        for i in range(1, self._file_list_widget.columnCount()):
            self._file_list_widget.resizeColumnToContents(i)
        set_status_tip(f"Currently under {self._pwd.name}", duration=1.0)

    def _set_busy(self, busy: bool):
        self._conn_btn.setEnabled(not busy)
        self._refresh_btn.setEnabled(not busy)
        self._last_dir_btn.setEnabled(not busy)
        self._up_one_btn.setEnabled(not busy)
        self._show_hidden_files_switch.setEnabled(not busy)
        self._file_list_widget.setEnabled(not busy)
        self._pwd_widget.setEnabled(not busy)

    def _host_name(self) -> str:
        username = self._user_name_edit.text()
        host = self._host_edit.text()
        return f"{username}@{host}"

    @thread_worker
    def _run_ls_command(self, path: Path) -> list[QtW.QTreeWidgetItem]:
        opt = "-lhAF" if self._show_hidden_files_switch.isChecked() else "-lhF"
        args = _make_ls_args(self._host_name(), path.as_posix(), options=opt)
        if self._is_wsl_switch.isChecked():
            args = ["wsl", "-e"] + args
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
        item_type = _item_type(item)
        if item_type == "d":
            self._set_current_path(self._pwd / item.text(0))
        elif item_type == "l":
            _, real_path = item.text(0).split(" -> ")
            args_check_type = _make_get_type_args(self._host_name(), real_path)
            if self._is_wsl_switch.isChecked():
                args_check_type = ["wsl", "-e"] + args_check_type
            result = subprocess.run(args_check_type, capture_output=True)
            if result.returncode != 0:
                raise ValueError(f"Failed to get type: {result.stderr.decode()}")
            link_type = result.stdout.decode().strip()
            if link_type == "directory":
                self._set_current_path(self._pwd / real_path)
            else:
                self._read_and_add_model(self._pwd / real_path)
        else:
            self._read_and_add_model(self._pwd / item.text(0))

    def _copy_item_paths(self, items: list[QtW.QTreeWidgetItem]):
        mime = self._make_mimedata_for_items(items)
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setMimeData(mime)

    def _send_files(self, paths: list[Path]):
        for path in paths:
            self._ui.submit_async_task(self._send_file, path, path.is_dir())

    def _make_reader_method(self, path: Path) -> SCPReaderMethod:
        return SCPReaderMethod(
            host=self._host_edit.text(),
            username=self._user_name_edit.text(),
            path=path,
            wsl=self._is_wsl_switch.isChecked(),
        )

    def _make_mimedata_for_items(
        self,
        items: list[QtW.QTreeWidgetItem],
    ) -> QtCore.QMimeData:
        urls: list[str] = []
        mime = QtCore.QMimeData()
        for item in items:
            item_type = _item_type(item)
            if item_type == "l":
                _, real_path = item.text(0).split(" -> ")
                remote_path = self._pwd / real_path
            else:
                remote_path = self._pwd / item.text(0)
            meth = self._make_reader_method(remote_path)
            urls.append(meth.to_str())
        mime.setText("\n".join([url for url in urls]))
        mime.setParent(self)
        return mime

    @thread_worker
    def _read_remote_path_worker(self, path: Path) -> WidgetDataModel:
        return self._make_reader_method(path).run()

    def _read_and_add_model(self, path: Path):
        """Read the remote file in another thread and add the model in the main."""
        worker = self._read_remote_path_worker(path)
        worker.returned.connect(self._ui.add_data_model)
        worker.started.connect(lambda: self._set_busy(True))
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()
        set_status_tip(f"Reading file: {path}", duration=2.0)

    def _on_pwd_edited(self):
        pwd_text = self._pwd_widget.text()
        if "*" in pwd_text or "?" in pwd_text:
            self._pwd_widget.setSelection(0, len(pwd_text))
            raise ValueError("Wildcards are not supported.")
        if self._pwd != Path(pwd_text):
            self._set_current_path(Path(pwd_text))

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
                set_status_tip(f"Sent to {self._host_name()}:{path.name}", duration=2.8)

    def update_configs(
        self,
        cfg: FileExplorerSSHConfig,
    ) -> None:
        self._host_edit.setText(cfg.default_host)
        self._user_name_edit.setText(cfg.default_user)
        self._is_wsl_switch.setChecked(cfg.default_use_wsl)
        if cfg.default_host and cfg.default_user and self._pwd == Path("~"):
            self._set_current_path(Path("~"))

    def _send_model(self, model: DragDataModel):
        data_model = model.data_model()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            src_pathobj = data_model.write_to_directory(tmpdir)
            self._send_file(src_pathobj)

    def _send_file(self, src: Path, is_dir: bool = False):
        """Send local file to the remote host."""
        dst_remote = self._pwd / src.name
        dst = f"{self._host_name()}:{dst_remote.as_posix()}"
        if is_dir:
            cmd = ["scp", "-r"]
        else:
            cmd = ["scp"]
        if self._is_wsl_switch.isChecked():
            drive = src.drive
            wsl_root = Path("mnt") / drive.lower().rstrip(":")
            src_pathobj_wsl = wsl_root / src.relative_to(drive).as_posix()[1:]
            src_wsl = "/" + src_pathobj_wsl.as_posix()
            args = ["wsl", "-e"] + cmd + [src_wsl, dst]
        else:
            args = cmd + [src.as_posix(), dst]
        subprocess.run(args)
        notify(f"Sent {src.as_posix()} to {dst_remote.as_posix()}", duration=2.8)


class QRemoteTreeWidget(QtW.QTreeWidget):
    item_copied = QtCore.Signal(list)
    item_pasted = QtCore.Signal(list)  # list of local Path objects

    def __init__(self, parent: QSSHRemoteExplorerWidget):
        super().__init__(parent)
        self.setIndentation(0)
        self.setColumnWidth(0, 180)
        self.setHeaderLabels(
            ["Name", "Datetime", "Size", "Group", "Owner", "Link", "Permission"]
        )
        self.header().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.header().setFixedHeight(20)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def parent(self) -> QSSHRemoteExplorerWidget:
        return super().parent()

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        open_action = menu.addAction("Open")
        open_action.triggered.connect(
            lambda: self.itemActivated.emit(self.currentItem(), 0)
        )
        copy_action = menu.addAction("Copy")
        copy_action.triggered.connect(
            lambda: self.item_copied.emit(self.selectedItems())
        )
        paste_action = menu.addAction("Paste")
        paste_action.triggered.connect(self._paste_from_clipboard)
        return menu

    def _show_context_menu(self, pos: QtCore.QPoint):
        self._make_context_menu().exec_(self.viewport().mapToGlobal(pos))

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


def _make_ls_args(host: str, path: str, options: str = "-AF") -> list[str]:
    return ["ssh", host, "ls", path + "/", options]


def _make_get_type_args(host: str, path: str) -> list[str]:
    return ["ssh", host, "stat", path, "--format='%F'"]


def _item_type(item: QtW.QTreeWidgetItem) -> str:
    """First character of the permission string."""
    return item.text(6)[0]


class QSeparator(QtW.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtW.QFrame.Shape.HLine)
        self.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        self.setFixedHeight(2)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )
