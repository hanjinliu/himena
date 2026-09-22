from __future__ import annotations

from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Iterator, Literal
from qtpy import QtWidgets as QtW, QtCore
from superqt import QToggleSwitch

from himena.qt._qsvg import QColoredSVGIcon
from himena.workflow import LocalReaderMethod
from himena.utils.cli import (
    to_wsl_path_from_wsl,
    to_windows_path_from_wsl,
)
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
    from himena_builtins.qt.explorer import (
        FileExplorerWSLConfig,
        FileExplorerWindowsConfig,
    )


class QWSLExplorerBase(QBaseRemoteExplorerWidget):
    def __init__(self, ui: MainWindowQt) -> None:
        super().__init__(ui)
        self._user = ""
        self._pwd = Path("~")
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

        layout.addWidget(labeled(self._pwd_label(), self._pwd_widget))

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

        self.themeChanged.connect(self._on_theme_changed)

    def _pwd_label(self) -> str:
        return "WSL:"

    def _on_theme_changed(self, theme) -> None:
        color = "#222222" if self._light_background else "#eeeeee"
        self._refresh_btn.setIcon(
            QColoredSVGIcon.fromfile(ICON_PATH / "refresh.svg", color)
        )

    def _set_busy(self, busy: bool):
        self._refresh_btn.setEnabled(not busy)
        self._last_dir_btn.setEnabled(not busy)
        self._up_one_btn.setEnabled(not busy)
        self._show_hidden_files_switch.setEnabled(not busy)
        self._file_list_widget.setEnabled(not busy)
        self._pwd_widget.setEnabled(not busy)

    def _ls_options(self) -> str:
        return "-lhAF" if self._show_hidden_files_switch.isChecked() else "-lhF"

    def _to_local_path(self, path: Path) -> Path:
        """Convert the path to the one that can be directly accessed locally."""
        raise NotImplementedError

    def _make_reader_method(self, path: Path, is_dir: bool) -> LocalReaderMethod:
        # files can be directly read via the local path, so that the opened
        # windows can also be saved to the original path.
        return LocalReaderMethod(path=self._to_local_path(path))

    def _copy_to_local(self, src: Path, dst: Path, is_dir: bool) -> None:
        src_local = self._to_local_path(src)
        if is_dir:
            shutil.copytree(src_local, dst)
        else:
            shutil.copy2(src_local, dst)

    def _send_file(self, src: Path, dst_remote: str, is_dir: bool = False):
        dst_local = self._to_local_path(Path(dst_remote))
        if is_dir:
            shutil.copytree(src, dst_local)
        else:
            shutil.copy2(src, dst_local)

    def _path_to_mime_text(self, path: Path) -> str:
        return str(self._to_local_path(path))


class QWSLRemoteExplorerWidget(QWSLExplorerBase):
    """A widget for exploring WSL files.

    This widget will execute `ls` commands to list files. Files are directly read from
    and copied to the corresponding local path, so that they can be saved back to the
    original location. This widget accepts copy-and-paste
    drag-and-drop from the local file system, including the normal explorer dock widget
    and the OS file explorer.
    """

    def _iter_file_items(self, path) -> Iterator[QtW.QTreeWidgetItem]:
        args = ["wsl", "-e", "ls", path + "/", self._ls_options()]
        yield from ls_args_to_items(args)

    def _get_file_type(self, path: str) -> Literal["d", "f"]:
        return stat_args_to_type(["wsl", "-e", "stat", path, "--format='%F'"])

    def _move_files(self, src: str, dst: str) -> None:
        exec_command(["wsl", "-e", "mv", src, dst])

    def _trash_files(self, paths: list[str]) -> None:
        exec_command(["wsl", "-e", "trash", *paths])

    def _set_current_path(self, path: Path):
        if (fp := path.as_posix()).startswith("~") and self._user:
            # The ~ in WSL is expanded to the Windows home directory.
            path = Path(f"/home/{self._user}/{fp[1:]}")
        return super()._set_current_path(path)

    def _to_local_path(self, path: Path) -> Path:
        return to_windows_path_from_wsl(path.as_posix())

    def update_configs(self, cfg: FileExplorerWSLConfig) -> None:
        self._user = cfg.default_user
        if self._last_dir == Path("~"):
            self._pwd = Path(f"/home/{self._user}")
            self._last_dir = Path(f"/home/{self._user}")
            # set the home directory
            self._set_current_path(self._pwd)


class QWindowsFromWSLRemoteExplorerWidget(QWSLExplorerBase):
    """A widget for exploring Windows files from WSL.

    This widget will execute `ls` commands to list files. Files are directly read from
    and copied to the corresponding local path, so that they can be saved back to the
    original location. This widget accepts copy-and-paste
    drag-and-drop from the local file system, including the normal explorer dock widget
    and the OS file explorer.
    """

    def _pwd_label(self) -> str:
        return "Win:"

    def _iter_file_items(self, path) -> Iterator[QtW.QTreeWidgetItem]:
        args = ["ls", to_wsl_path_from_wsl(path), self._ls_options()]
        yield from ls_args_to_items(args)

    def _get_file_type(self, path: str) -> Literal["d", "f"]:
        return stat_args_to_type(["stat", to_wsl_path_from_wsl(path), "--format='%F'"])

    def _move_files(self, src: str, dst: str) -> None:
        exec_command(["mv", to_wsl_path_from_wsl(src), to_wsl_path_from_wsl(dst)])

    def _trash_files(self, paths: list[str]) -> None:
        raise NotImplementedError("Cannot trash windows files from WSL")

    def _to_local_path(self, path: Path) -> Path:
        return Path(to_wsl_path_from_wsl(path.as_posix()))

    def update_configs(self, cfg: FileExplorerWindowsConfig) -> None:
        self._user = cfg.default_user
        if self._last_dir == Path("~"):
            self._pwd = Path(f"C:/Users/{self._user}")
            self._last_dir = Path(f"C:/Users/{self._user}")
            # set the home directory
            self._set_current_path(self._pwd)
