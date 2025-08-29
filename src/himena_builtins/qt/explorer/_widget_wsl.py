from __future__ import annotations

import getpass
from pathlib import Path
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore
from superqt import QToggleSwitch

from himena.qt._qsvg import QColoredSVGIcon
from himena.workflow import WslReaderMethod
from himena.utils.cli import local_to_wsl
from himena.widgets import set_status_tip
from himena_builtins._consts import ICON_PATH
from himena_builtins.qt.explorer._base import QBaseRemoteExplorerWidget
from himena_builtins.qt.widgets._shared import labeled

if TYPE_CHECKING:
    from himena.qt import MainWindowQt


class QWSLRemoteExplorerWidget(QBaseRemoteExplorerWidget):
    """A widget for exploring WSL files.

    This widget will execute `ls` and `cp` commands to list, read and send files when
    needed. This widget accepts copy-and-paste drag-and-drop from the local
    file system, including the normal explorer dock widget and the OS file explorer.
    """

    def __init__(self, ui: MainWindowQt) -> None:
        super().__init__(ui)
        self._pwd = Path("/home", getpass.getuser())
        self._last_dir = self._pwd

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

        layout = QtW.QVBoxLayout(self)

        layout.addWidget(labeled("WSL:", self._pwd_widget))

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

        self._refresh_btn.clicked.connect(self._refresh_pwd)
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

        # set the home directory
        self._set_current_path(self._pwd)
        self.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme) -> None:
        color = "#222222" if self._light_background else "#eeeeee"
        self._refresh_btn.setIcon(
            QColoredSVGIcon.fromfile(ICON_PATH / "refresh.svg", color)
        )

    def _make_ls_args(self, path: str):
        opt = "-lhAF" if self._show_hidden_files_switch.isChecked() else "-lhF"
        return ["wsl", "-e", "ls", path + "/", opt]

    def _make_get_type_args(self, path: str) -> list[str]:
        return ["stat", path, "--format='%F'"]

    def _make_move_args(self, src: str, dst: str) -> list[str]:
        return ["wsl", "-e", "mv", src, dst]

    def _make_trash_args(self, paths: list[str]) -> list[str]:
        return ["wsl", "-e", "trash", *paths]

    def _make_local_to_remote_args(self, src, dst_remote, is_dir: bool = False):
        return local_to_wsl(src, dst_remote, is_dir=is_dir)

    def _set_current_path(self, path: Path):
        fp = path.as_posix()
        if fp.startswith("~"):
            fp = f"/home/{getpass.getuser()}/{fp[1:]}"
        self._pwd_widget.setText(fp)
        self._file_list_widget.clear()
        worker = self._run_ls_command(path)
        worker.returned.connect(self._on_ls_done)
        worker.started.connect(lambda: self._set_busy(True))
        worker.finished.connect(lambda: self._set_busy(False))
        worker.start()
        set_status_tip("Obtaining the file content ...", duration=3.0)

    def _set_busy(self, busy: bool):
        self._refresh_btn.setEnabled(not busy)
        self._last_dir_btn.setEnabled(not busy)
        self._up_one_btn.setEnabled(not busy)
        self._show_hidden_files_switch.setEnabled(not busy)
        self._file_list_widget.setEnabled(not busy)
        self._pwd_widget.setEnabled(not busy)

    def _make_reader_method(self, path: Path, is_dir: bool) -> WslReaderMethod:
        return WslReaderMethod(path=path, force_directory=is_dir)

    def _make_reader_method_from_str(self, line: str, is_dir: bool) -> WslReaderMethod:
        return WslReaderMethod.from_str(line, force_directory=is_dir)
