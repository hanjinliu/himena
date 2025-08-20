from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt import QToggleSwitch

from himena.qt._qsvg import QColoredSVGIcon
from himena.workflow import RemoteReaderMethod
from himena.consts import MonospaceFontFamily
from himena.utils.cli import local_to_remote
from himena_builtins._consts import ICON_PATH
from himena_builtins.qt.explorer._base import QBaseRemoteExplorerWidget
from himena_builtins.qt.widgets._shared import labeled

if TYPE_CHECKING:
    from himena_builtins.qt.explorer import FileExplorerSSHConfig
    from himena.qt import MainWindowQt


class QSSHRemoteExplorerWidget(QBaseRemoteExplorerWidget):
    """A widget for exploring remote files via SSH.

    This widget will execute `ls`, `ssh` and `scp` commands to list, read and send
    files when needed. This widget accepts copy-and-paste drag-and-drop from the local
    file system, including the normal explorer dock widget and the OS file explorer.

    If you are using Windows, checking the "Use WSL" switch will forward all the
    subprocess commands to WSL.
    """

    def __init__(self, ui: MainWindowQt) -> None:
        super().__init__(ui)
        font = QtGui.QFont(MonospaceFontFamily)
        self._host_edit = QtW.QLineEdit()
        self._host_edit.setFont(font)
        self._host_edit.setMaximumWidth(100)
        self._user_name_edit = QtW.QLineEdit()
        self._user_name_edit.setFont(font)
        self._user_name_edit.setMaximumWidth(80)
        self._port_edit = QtW.QLineEdit()
        self._port_edit.setFont(font)
        self._port_edit.setValidator(QtGui.QIntValidator(0, 65535))
        self._port_edit.setMaximumWidth(40)
        self._is_wsl_switch = QToggleSwitch()
        self._is_wsl_switch.setText("Use WSL")
        self._is_wsl_switch.setFixedHeight(24)
        self._is_wsl_switch.setChecked(False)
        self._is_wsl_switch.setVisible(sys.platform == "win32")
        self._is_wsl_switch.setToolTip(
            "Use WSL (Windows Subsystem for Linux) to access remote files. If \n "
            "checked, all the subprocess commands such as `ls` will be prefixed \n"
            "with `wsl -e`."
        )
        self._protocol_choice = QtW.QComboBox()
        self._protocol_choice.addItems(["rsync", "scp"])
        self._protocol_choice.setCurrentIndex(0)
        self._protocol_choice.setToolTip("Choose the protocol to send files.")

        self._show_hidden_files_switch = QToggleSwitch()
        self._show_hidden_files_switch.setText("Hidden Files")
        self._show_hidden_files_switch.setToolTip("Also show hidden files")
        self._show_hidden_files_switch.setFixedHeight(24)
        self._show_hidden_files_switch.setChecked(False)

        self._last_dir_btn = QtW.QPushButton("←")
        self._last_dir_btn.setFixedWidth(20)
        self._last_dir_btn.setToolTip("Back to last directory")

        self._up_one_btn = QtW.QPushButton("↑")
        self._up_one_btn.setFixedWidth(20)
        self._up_one_btn.setToolTip("Up one directory")
        self._refresh_btn = QtW.QToolButton()
        self._refresh_btn.setToolTip("Refresh current directory")

        self._conn_btn = QtW.QPushButton("Connect")
        self._conn_btn.setFixedWidth(60)
        self._conn_btn.setToolTip("Connect to the remote host with the given user name")

        layout = QtW.QVBoxLayout(self)

        hlayout0 = QtW.QHBoxLayout()
        hlayout0.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hlayout0)
        hlayout0.addWidget(labeled("Host:", self._host_edit, label_width=30), 3)
        hlayout0.addWidget(labeled("User:", self._user_name_edit, label_width=30), 2)
        hlayout0.addWidget(labeled("Port:", self._port_edit, label_width=30), 2)

        hlayout1 = QtW.QHBoxLayout()
        hlayout1.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hlayout1)
        hlayout1.addWidget(self._is_wsl_switch)
        hlayout1.addWidget(self._protocol_choice)
        hlayout1.addWidget(self._conn_btn)

        layout.addWidget(QSeparator())
        layout.addWidget(labeled("Path:", self._pwd_widget))

        hlayout2 = QtW.QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.addWidget(self._last_dir_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hlayout2.addWidget(self._up_one_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hlayout2.addWidget(QtW.QWidget(), 100)  # spacer
        hlayout2.addWidget(self._show_hidden_files_switch)
        hlayout2.addWidget(self._refresh_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addLayout(hlayout2)
        layout.addWidget(self._filter_widget)
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
        self._light_background = True
        self.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme) -> None:
        color = "#222222" if self._light_background else "#eeeeee"
        self._refresh_btn.setIcon(
            QColoredSVGIcon.fromfile(ICON_PATH / "refresh.svg", color)
        )

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

    def _make_reader_method(self, path: Path, is_dir: bool) -> RemoteReaderMethod:
        return RemoteReaderMethod(
            host=self._host_edit.text(),
            username=self._user_name_edit.text(),
            path=path,
            port=int(self._port_edit.text()),
            wsl=self._is_wsl_switch.isChecked(),
            protocol=self._protocol_choice.currentText(),
            force_directory=is_dir,
        )

    def _make_ls_args(self, path):
        opt = "-lhAF" if self._show_hidden_files_switch.isChecked() else "-lhF"
        port = int(self._port_edit.text())
        host = self._host_name()
        args = ["ssh", "-p", str(port), host, "ls", path + "/", opt]

        if self._is_wsl_switch.isChecked():
            args = ["wsl", "-e"] + args
        return args

    def _make_get_type_args(self, path: str) -> list[str]:
        host = self._host_name()
        port = int(self._port_edit.text())
        args = ["ssh", "-p", str(port), host, "stat", path, "--format='%F'"]
        if self._is_wsl_switch.isChecked():
            args = ["wsl", "-e"] + args
        return args

    def readers_from_mime(self, mime: QtCore.QMimeData) -> list[RemoteReaderMethod]:
        """Construct readers from the mime data."""
        is_wsl = self._is_wsl_switch.isChecked()
        prot = self._protocol_choice.currentText()
        out: list[RemoteReaderMethod] = []
        for line in mime.html().split("<br>"):
            if not line:
                continue
            if m := re.compile(r"<span ftype=\"(d|f)\">(.+)</span>").match(line):
                is_dir = m.group(1) == "d"
                line = m.group(2)
            else:
                continue
            meth = RemoteReaderMethod.from_str(
                line,
                wsl=is_wsl,
                protocol=prot,
                force_directory=is_dir,
            )
            out.append(meth)
        return out

    def update_configs(
        self,
        cfg: FileExplorerSSHConfig,
    ) -> None:
        self._host_edit.setText(cfg.default_host)
        self._user_name_edit.setText(cfg.default_user)
        self._port_edit.setText(str(cfg.default_port))
        self._is_wsl_switch.setChecked(cfg.default_use_wsl)
        self._protocol_choice.setCurrentText(cfg.default_protocol)
        if cfg.default_host and cfg.default_user and self._pwd == Path("~"):
            self._set_current_path(Path("~"))

    def _make_local_to_remote_args(
        self, src: Path, dst_remote: str, is_dir: bool = False
    ) -> list[str]:
        return local_to_remote(
            self._protocol_choice.currentText(),
            src,
            f"{self._host_name()}:{dst_remote}",
            is_wsl=self._is_wsl_switch.isChecked(),
            is_dir=is_dir,
            port=int(self._port_edit.text()),
        )


class QSeparator(QtW.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtW.QFrame.Shape.HLine)
        self.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        self.setFixedHeight(2)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )
