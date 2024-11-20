from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW, QtCore

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.plugins import protocol_override
from himena.qt._utils import get_main_window


class QReaderNotFoundWidget(QtW.QWidget):
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

    @protocol_override
    def update_model(self, model: WidgetDataModel[Path]):
        self._file_path = model.value
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

    @protocol_override
    def to_model(self) -> WidgetDataModel[Path]:
        return WidgetDataModel(
            value=self._file_path,
            type=self.model_type(),
        )

    @protocol_override
    def model_type(self) -> str:
        return StandardType.READER_NOT_FOUND

    @protocol_override
    def is_modified(self) -> bool:
        return False

    @protocol_override
    def set_modified(self, modified: bool) -> None:
        pass

    def _open_as_text(self):
        get_main_window(self).exec_action("builtins:open-as-text-anyway")
