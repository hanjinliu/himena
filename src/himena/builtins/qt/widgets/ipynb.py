from __future__ import annotations

from pydantic_compat import BaseModel, Field, field_validator
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore

from himena.consts import StandardType, MonospaceFontFamily
from himena.types import WidgetDataModel
from himena.plugins import protocol_override

from himena.builtins.qt.widgets._text_base import QMainTextEdit


class QIpynbEdit(QtW.QScrollArea):
    def __init__(self):
        super().__init__()
        self._central_widget = QtW.QWidget()
        self.setWidget(self._central_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cell_widgets: list[QIpynbCellEdit] = []
        _layout = QtW.QVBoxLayout(self._central_widget)
        _layout.setContentsMargins(0, 0, 0, 0)
        self._layout = _layout
        self._ipynb_orig = IpynbFile()
        self._model_type = StandardType.IPYNB

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        if not isinstance(value := model.value, str):
            value = str(value)
        self._ipynb_orig = IpynbFile.model_validate_json(value)
        self.clear_all()
        for idx, cell in enumerate(self._ipynb_orig.cells):
            self.insert_cell(idx, cell)
        self._model_type = model.type
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        ipynb = self._ipynb_orig.model_copy()
        for idx, widget in enumerate(self._cell_widgets):
            ipynb.cells[idx].source = widget._text_edit.toPlainText()
        js_string = ipynb.model_dump_json(indent=2)
        return WidgetDataModel(
            type=self.model_type(),
            value=js_string,
        )

    @protocol_override
    def model_type(self) -> str:
        return self._model_type

    @protocol_override
    def is_modified(self) -> bool:
        return any(
            widget._text_edit.isWindowModified() for widget in self._cell_widgets
        )

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 360

    @protocol_override
    def display_name(self) -> str:
        return "Built-in Jupyter Notebook Editor"

    def clear_all(self):
        for child in self._cell_widgets:
            self._layout.removeWidget(child)
            child.deleteLater()
        self._cell_widgets.clear()

    def insert_cell(self, idx: int, cell: IpynbCell):
        widget = QIpynbCellEdit(cell, self._ipynb_orig.language)
        self._layout.insertWidget(idx, widget)
        self._cell_widgets.insert(idx, widget)


class QIpynbCellEdit(QtW.QGroupBox):
    def __init__(self, cell: IpynbCell, language: str):
        super().__init__()
        self._text_edit = QMainTextEdit()
        self._text_edit.setPlainText(cell.source)
        lang = language if cell.cell_type == "code" else cell.cell_type
        self._text_edit.syntax_highlight(lang)
        self._language_label = QtW.QLabel(lang.title())
        font = QtGui.QFont(MonospaceFontFamily)
        font.setPointSize(10)
        self._language_label.setFont(font)
        self._language_label.setFixedHeight(14)
        self._language_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        _layout = QtW.QVBoxLayout(self)
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setSpacing(0)
        _layout.addWidget(self._text_edit)

        _footer_layout = QtW.QHBoxLayout()
        _footer_layout.addWidget(self._language_label)
        _layout.addLayout(_footer_layout)

        self._text_edit.textChanged.connect(self._on_text_changed)
        self._height_for_font = self._text_edit.fontMetrics().height()

    def _on_text_changed(self):
        nblocks = self._text_edit.blockCount()
        height = self._height_for_font * min(nblocks, 10)
        self._text_edit.setFixedHeight(height)


class IpynbCell(BaseModel):
    cell_type: str = Field(
        default="code",
        description="Type of cell, such as 'code' or 'markdown'",
    )
    metadata: dict = Field(default_factory=dict)
    source: str = Field("")

    @field_validator("source", mode="before")
    def _source_to_str(cls, v) -> str:
        if isinstance(v, list):
            return "".join(v)
        return v

    @property
    def output(self) -> list:
        return self.metadata.get("outputs", [])


class IpynbMetadata(BaseModel):
    kernel_info: dict = Field(default_factory=dict)
    language_info: dict = Field(default_factory=dict)


class IpynbFile(BaseModel):
    metadata: IpynbMetadata = Field(default_factory=IpynbMetadata)
    nbformat: int | None = Field(None)
    nbformat_minor: int | None = Field(None)
    cells: list[IpynbCell] = Field(default_factory=list)

    @property
    def language(self) -> str:
        lang = self.metadata.language_info.get("name")
        if lang is None:
            lang = "python"
        return lang
