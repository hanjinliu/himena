from __future__ import annotations

import getpass
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Literal
from qtpy import QtWidgets as QtW, QtCore
from superqt import QToggleSwitch

from himena.qt._qsvg import QColoredSVGIcon
from himena.workflow import WslReaderMethod
from himena.utils.cli import local_to_wsl
from himena_builtins._consts import ICON_PATH
from himena_builtins.qt.explorer._base import (
    QBaseRemoteExplorerWidget,
    ls_args_to_items,
    exec_command,
    stat_args_to_type,
)
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
        self._refresh_btn.setToolTip("Refresh current directory (F5)")

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

    def _iter_file_items(self, path) -> Iterator[QtW.QTreeWidgetItem]:
        opt = "-lhAF" if self._show_hidden_files_switch.isChecked() else "-lhF"
        args = ["wsl", "-e", "ls", path + "/", opt]
        yield from ls_args_to_items(args)

    def _get_file_type(self, path: str) -> Literal["d", "f"]:
        return stat_args_to_type(["stat", path, "--format='%F'"])

    def _move_files(self, src: str, dst: str) -> None:
        exec_command(["wsl", "-e", "mv", src, dst])

    def _trash_files(self, paths: list[str]) -> None:
        exec_command(["wsl", "-e", "trash", *paths])

    def _send_file_args(self, src, dst_remote, is_dir: bool = False):
        return local_to_wsl(src, dst_remote, is_dir=is_dir)

    def _send_file(self, src, dst_remote, is_dir: bool = False):
        exec_command(self._send_file_args(src, dst_remote, is_dir=is_dir))

    def _set_current_path(self, path: Path):
        if (fp := path.as_posix()).startswith("~"):
            # The ~ in WSL is expanded to the Windows home directory.
            path = Path(f"/home/{getpass.getuser()}/{fp[1:]}")
        return super()._set_current_path(path)

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
