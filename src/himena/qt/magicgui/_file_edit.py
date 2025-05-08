from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from magicgui.widgets import show_file_dialog
from magicgui.widgets.bases import ValueWidget
from magicgui.types import FileDialogMode, Undefined
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app

_MULTI_FILE_SEPARATOR = ";"


class QFileEdit(QtW.QWidget):
    valueChanged = QtCore.Signal(str)

    def __init__(self, mode=FileDialogMode.EXISTING_FILE, filter=None, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._line_edit = QtW.QLineEdit(self)
        self._btn = QtW.QPushButton("...", self)
        self._btn.setToolTip("Browse file(s) ...")
        self._line_edit.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
        )
        self._mode = FileDialogMode(mode)
        self._filter = filter
        self._line_edit.setPlaceholderText("Enter, select or drop file(s)")

        layout = QtW.QHBoxLayout(self)
        layout.addWidget(self._line_edit)
        layout.addWidget(self._btn)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn.clicked.connect(self._open_file_dialog)

    def value(self) -> Path | list[Path] | None:
        _p = self._line_edit.text()
        if _p:
            if self._mode is FileDialogMode.EXISTING_FILES:
                return [
                    Path(p).expanduser().absolute()
                    for p in _p.split(_MULTI_FILE_SEPARATOR)
                ]
            else:
                return Path(_p.split(_MULTI_FILE_SEPARATOR)[0]).expanduser().absolute()
        return None

    def set_value(self, value: Path | list[Path] | None):
        if value is None:
            self._line_edit.clear()
        elif isinstance(value, list):
            if self._mode is not FileDialogMode.EXISTING_FILES:
                raise ValueError("Cannot set multiple files in this file mode")
            self._line_edit.setText(_MULTI_FILE_SEPARATOR.join(str(p) for p in value))
        else:
            self._line_edit.setText(str(value))

    def _open_file_dialog(self):
        _start_path = None
        if _p := self._line_edit.text():
            _fp = Path(_p.split(_MULTI_FILE_SEPARATOR)[0]).expanduser().absolute()
            if _fp.exists():
                _start_path = str(_fp)

        match self._mode:
            case FileDialogMode.EXISTING_DIRECTORY:
                _caption = "Choose directory"
            case FileDialogMode.EXISTING_FILES:
                _caption = "Select files"
            case _:
                _caption = "Select file"

        if file_path := show_file_dialog(
            self._mode,
            caption=_caption,
            start_path=_start_path,
            filter=self._filter,
            parent=self,
        ):
            self._line_edit.setText(file_path)

    def _accept_urls(self, urls: list[QtCore.QUrl]) -> bool:
        if len(urls) == 1:
            path = Path(urls[0].toLocalFile())
            if (
                self._mode is FileDialogMode.EXISTING_FILE
                and path.is_file()
                or self._mode is FileDialogMode.EXISTING_DIRECTORY
                and path.is_dir()
                or self._mode is FileDialogMode.EXISTING_FILES
                and path.is_file()
                or self._mode is FileDialogMode.OPTIONAL_FILE
                and path.is_file()
            ):
                return True
        else:
            if self._mode is FileDialogMode.EXISTING_FILES:
                return True
        return False

    def _set_urls(self, urls: list[QtCore.QUrl]):
        if urls:
            self._line_edit.setText(
                _MULTI_FILE_SEPARATOR.join(url.toLocalFile() for url in urls)
            )

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if self._accept_urls(event.mimeData().urls()):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        self._set_urls(event.mimeData().urls())


class QBaseFileEdit(QBaseValueWidget):
    def __init__(self, **kwargs) -> None:
        super().__init__(QFileEdit, "value", "set_value", "valueChanged", **kwargs)


class FileEdit(ValueWidget["Path | list[Path]"]):
    def __init__(
        self,
        mode: FileDialogMode = FileDialogMode.EXISTING_FILE,
        filter: str | None = None,
        value=Undefined,
        **kwargs,
    ):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QBaseFileEdit,
            backend_kwargs={"mode": mode, "filter": filter},
            **kwargs,
        )
