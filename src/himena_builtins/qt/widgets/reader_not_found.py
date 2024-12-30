from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW, QtCore

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.plugins import validate_protocol
from himena.qt._utils import get_main_window


class QReaderNotFound(QtW.QWidget):
    """No reader function is defined for the file.

    The content of the file is not read yet. This widget only contains the file path.
    """

    __himena_widget_id__ = "builtins:QReaderNotFound"

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._label = QtW.QLabel("Reader not found.")
        self._label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._label.setWordWrap(True)
        self._open_as_text_button = QtW.QPushButton("Open as text")
        self._open_as_text_button.clicked.connect(self._open_as_text)
        self._file_path: Path | None = None

        layout.addWidget(self._label)
        layout.addWidget(self._open_as_text_button)

    @validate_protocol
    def update_model(self, model: WidgetDataModel[Path]):
        self._file_path = model.value
        if not self._file_path.exists():
            self._label.setText(f"File not found: {self._file_path}")
            return
        _byte = self._file_path.stat().st_size
        if _byte < 1024:
            _size = f"{_byte} B"
        elif _byte < 1024**2:
            _size = f"{_byte / 1024:.2f} KB"
        elif _byte < 1024**3:
            _size = f"{_byte / 1024 ** 2:.2f} MB"
        else:
            _size = f"{_byte / 1024 ** 3:.2f} GB"
        self._label.setText(f"Reader not found for {model.value.name} ({_size})")

    @validate_protocol
    def to_model(self) -> WidgetDataModel[Path]:
        return WidgetDataModel(
            value=self._file_path,
            type=self.model_type(),
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.READER_NOT_FOUND

    def _open_as_text(self):
        get_main_window(self).exec_action("builtins:open-as-text-anyway")
