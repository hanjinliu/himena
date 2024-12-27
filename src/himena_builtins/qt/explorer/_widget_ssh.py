from __future__ import annotations

import sys
import subprocess
import tempfile
from pathlib import Path
from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt.utils import thread_worker

from himena._descriptors import SCPReaderMethod
from himena import _drag
from himena.consts import MonospaceFontFamily
from himena.types import DragDataModel, WidgetDataModel
from himena.widgets import MainWindow, set_status_tip, notify
from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena_builtins.qt.widgets._shared import labeled


class QSSHRemoteExplorerWidget(QtW.QWidget):
    on_ls = QtCore.Signal(object)

    def __init__(self, ui: MainWindow) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        font = QtGui.QFont(MonospaceFontFamily)
        self._ui = ui
        self._ip_address_edit = QtW.QLineEdit()
        self._ip_address_edit.setFont(font)
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
        self._show_hidden_files_switch.setText("Show Hidden Files")
        self._show_hidden_files_switch.setFixedHeight(24)
        self._show_hidden_files_switch.setChecked(False)

        self._pwd_widget = QtW.QLineEdit()
        self._pwd_widget.setReadOnly(True)
        self._pwd_widget.setFont(font)
        self._edit_pwd_btn = QtW.QPushButton("Edit")
        self._edit_pwd_btn.clicked.connect(self._on_edit_pwd_clicked)

        self._last_dir_btn = QtW.QPushButton("<")
        self._last_dir_btn.setFixedWidth(20)
        self._last_dir_btn.setToolTip("Go to last directory")

        self._up_one_btn = QtW.QPushButton("↑")
        self._up_one_btn.setFixedWidth(20)
        self._up_one_btn.setToolTip("Up one directory")
        self._refresh_btn = QtW.QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(60)
        self._refresh_btn.setToolTip("Refresh current directory")

        self._set_btn = QtW.QPushButton("Set")
        self._set_btn.setFixedWidth(40)
        self._set_btn.setToolTip("Set host/user and refresh")
        self._buttons = QtW.QWidget()
        _button_layout = QtW.QHBoxLayout(self._buttons)
        _button_layout.setContentsMargins(0, 0, 0, 0)
        _button_layout.addWidget(
            self._last_dir_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft
        )
        _button_layout.addWidget(self._up_one_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        _button_layout.addWidget(QtW.QWidget())
        _button_layout.addWidget(
            self._refresh_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        _button_layout.addWidget(self._set_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        self._file_list_widget = QtW.QTreeWidget()
        self._file_list_widget.itemActivated.connect(self._on_item_double_clicked)
        self._file_list_widget.setFont(font)
        self._file_list_widget.setHeaderLabels(
            ["Name", "Datetime", "Size", "Group", "Owner", "Link", "Permission"]
        )
        self._file_list_widget.header().setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self._file_list_widget.header().setFixedHeight(20)

        self._pwd = Path("~")
        self._last_dir = Path("~")
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(labeled("IP Address:", self._ip_address_edit))
        layout.addWidget(labeled("User Name:", self._user_name_edit))
        layout.addWidget(self._is_wsl_switch)
        layout.addWidget(self._show_hidden_files_switch)
        layout.addWidget(labeled("Path:", self._pwd_widget, self._edit_pwd_btn))
        layout.addWidget(self._buttons)
        layout.addWidget(self._file_list_widget)

        self._set_btn.clicked.connect(lambda: self._set_current_path(Path("~")))
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
        self._last_dir = self._pwd
        self._pwd = path
        self._pwd_widget.setText(self._pwd.as_posix())
        self._file_list_widget.clear()
        worker = self._run_ls_command(path)
        worker.returned.connect(self._on_ls_done)
        worker.start()
        set_status_tip("Obtaining the file content ...")

    def _on_ls_done(self, items: list[QtW.QTreeWidgetItem]):
        self._file_list_widget.addTopLevelItems(items)
        for i in range(1, self._file_list_widget.columnCount()):
            self._file_list_widget.resizeColumnToContents(i)

    def _host_name(self) -> str:
        username = self._user_name_edit.text()
        ip_address = self._ip_address_edit.text()
        return f"{username}@{ip_address}"

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
        # format of ls -l is:
        # <permission> <link> <owner> <group> <size> <month> <day> <time> <name>
        items: list[QtW.QTreeWidgetItem] = []
        for row in rows[1:]:  # the first line is total size
            *others, month, day, time, name = row.split(maxsplit=8)
            datetime = f"{month} {day} {time}"
            item = QtW.QTreeWidgetItem([name, datetime] + others[::-1])
            item.setToolTip(0, name)
            items.append(item)

        # sort directories first
        items = sorted(
            items,
            key=lambda x: (x.text(0).endswith("/"), x.text(0)),
            reverse=True,
        )

        return items

    def _on_item_double_clicked(self, item: QtW.QTreeWidgetItem):
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
                self._ui.add_data_model(self._read_remote_path(self._pwd / real_path))
        else:
            self._ui.add_data_model(self._read_remote_path(self._pwd / item.text(0)))

    def _read_remote_path(self, path: Path) -> WidgetDataModel:
        method = SCPReaderMethod(
            ip_address=self._ip_address_edit.text(),
            username=self._user_name_edit.text(),
            path=path,
            wsl=self._is_wsl_switch.isChecked(),
        )
        return method.get_model(self._ui.model_app)

    def _on_edit_pwd_clicked(self):
        if self._edit_pwd_btn.text() == "Edit":
            self._pwd_widget.setReadOnly(False)
            self._edit_pwd_btn.setText("OK")
        else:
            self._set_current_path(Path(self._pwd_widget.text()))
            self._pwd_widget.setReadOnly(True)
            self._edit_pwd_btn.setText("Edit")

    def dragEnterEvent(self, a0):
        if _drag.get_dragging_model() is not None:
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

    def update_config(
        self,
        default_host: str = "",
        default_user: str = "",
        default_use_wsl: bool = False,
    ) -> None:
        self._ip_address_edit.setText(default_host)
        self._user_name_edit.setText(default_user)
        self._is_wsl_switch.setChecked(default_use_wsl)

    def _send_model(self, model: DragDataModel):
        data_model = model.data_model()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            src_pathobj = data_model.write_to_directory(tmpdir)
            dst_remote = self._pwd / src_pathobj.name
            dst = f"{self._host_name()}:{dst_remote.as_posix()}"
            if self._is_wsl_switch.isChecked():
                drive = src_pathobj.drive
                wsl_root = Path("mnt") / drive.lower().rstrip(":")
                src_pathobj_wsl = (
                    wsl_root / src_pathobj.relative_to(drive).as_posix()[1:]
                )
                src_wsl = "/" + src_pathobj_wsl.as_posix()
                args = ["wsl", "-e", "scp", src_wsl, dst]
            else:
                args = ["scp", src_pathobj.as_posix(), dst]
            subprocess.run(args)
            notify(f"Sent to {dst_remote.as_posix()}", duration=2.8)


def _make_ls_args(host: str, path: str, options: str = "-AF") -> list[str]:
    return ["ssh", host, "ls", path + "/", options]


def _make_get_type_args(host: str, path: str) -> list[str]:
    return ["ssh", host, "stat", path, "--format='%F'"]


def _item_type(item: QtW.QTreeWidgetItem) -> str:
    """First character of the permission string."""
    return item.text(1)[0]
