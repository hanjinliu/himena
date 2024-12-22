from __future__ import annotations
import weakref

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QIconifyIcon

from himena.consts import StandardType, MonospaceFontFamily
from himena.qt import drag_model, ndarray_to_qimage
from himena import _drag
from himena.standards.model_meta import TextMeta
from himena.standards import ipynb
from himena.style import Theme
from himena.types import WidgetDataModel
from himena.plugins import validate_protocol

from himena_builtins.qt.widgets._text_base import QMainTextEdit


class QIpynbEdit(QtW.QScrollArea):
    """The built-in ipynb (Jupyter Notebook) editor widget.

    ## Basic Usage

    This widget is only for editing Jupyter Notebook files. It can add or delete cells,
    edit cells and move cells. Running the code is not supported.

    ## Drag and Drop

    Each cell can be dragged out. The model has type `StandardType.TEXT` ("text"). If
    the data is dropped in the same widget, the cell will be moved, otherwise the cell
    content will be copied.
    """

    __himena_widget_id__ = "builtins:QIpynbEdit"
    __himena_widget_name__ = "Built-in Jupyter Notebook Editor"

    def __init__(self):
        super().__init__()
        self._central_widget = QtW.QWidget()
        self.setWidget(self._central_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cell_widgets: list[QIpynbCellEdit] = []
        _layout = QtW.QVBoxLayout(self._central_widget)
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self._layout = _layout
        self._ipynb_orig = ipynb.IpynbFile()
        self._model_type = StandardType.IPYNB
        self._dragging_index: int | None = None
        self._text_theme = "default"
        self._control_widget = QIpynbControl(self)
        self._is_editable = True

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if not isinstance(value := model.value, str):
            value = str(value)
        self._ipynb_orig = ipynb.IpynbFile.model_validate_json(value)
        self.clear_all()
        for idx, cell in enumerate(self._ipynb_orig.cells):
            self.insert_cell(idx, cell)
        self._model_type = model.type
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        ipynb = self._ipynb_orig.model_copy()
        for idx, widget in enumerate(self._cell_widgets):
            ipynb.cells[idx].source = widget.text()
        js_string = ipynb.model_dump_json(indent=2)
        return WidgetDataModel(
            type=self.model_type(),
            value=js_string,
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return any(
            widget._text_edit.isWindowModified() for widget in self._cell_widgets
        )

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        if theme.is_light_background():
            self._text_theme = "default"
        else:
            self._text_theme = "native"
        for widget in self._cell_widgets:
            widget._text_edit._code_theme = self._text_theme
            widget._text_edit.syntax_highlight(widget._text_edit._language)

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 360

    @validate_protocol
    def is_editable(self) -> bool:
        return self._is_editable

    @validate_protocol
    def set_editable(self, editable: bool):
        self._is_editable = editable
        for widget in self._cell_widgets:
            widget._text_edit.setReadOnly(not editable)
        self._control_widget._insert_cell_btn.setEnabled(editable)
        self._control_widget._insert_md_btn.setEnabled(editable)
        self._control_widget._delete_cell_btn.setEnabled(editable)

    @validate_protocol
    def control_widget(self) -> QtW.QWidget:
        return self._control_widget

    def clear_all(self):
        for child in self._cell_widgets:
            self._layout.removeWidget(child)
            child.deleteLater()
        self._cell_widgets.clear()

    def insert_cell(self, idx: int, cell: ipynb.IpynbCell):
        widget = QIpynbCellEdit(cell, self._ipynb_orig.language, self)
        self._layout.insertWidget(idx, widget)
        self._cell_widgets.insert(idx, widget)

    def delete_cell(self, idx: int):
        widget = self._cell_widgets.pop(idx)
        self._layout.removeWidget(widget)
        widget.deleteLater()

    def current_index(self) -> int:
        for idx, widget in enumerate(self._cell_widgets):
            if widget._text_edit.hasFocus() or widget.hasFocus():
                return idx
        return -1


class QDraggableArea(QtW.QWidget):
    dragged = QtCore.Signal()

    def __init__(self):
        super().__init__()
        icon = QIconifyIcon("qlementine-icons:drag-16", color="#777777")
        self._icon = icon
        self._pixmap = icon.pixmap(100, 100)

        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self._pressed = False
        self.setToolTip("Drag area")

    def paintEvent(self, a0):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        target_rect = self.rect()
        painter.drawPixmap(target_rect, self._pixmap)

    def mousePressEvent(self, a0):
        if a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pressed = True

    def mouseMoveEvent(self, a0):
        if self._pressed:
            self._pressed = False
            self.dragged.emit()

    def mouseReleaseEvent(self, a0):
        self._pressed = False


class QIpynbCellEdit(QtW.QGroupBox):
    """Widget for a single cell."""

    def __init__(self, cell: ipynb.IpynbCell, language: str, parent: QIpynbEdit):
        super().__init__(parent)
        self._ipynb_cell = cell
        self.setAcceptDrops(True)
        self._ipynb_edit_ref = weakref.ref(parent)
        self._text_edit = QMainTextEdit()
        self._text_edit._code_theme = parent._text_theme
        self._text_edit.setPlainText(cell.source)
        self._text_edit.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        lang = language if cell.cell_type == "code" else cell.cell_type
        self._text_edit.syntax_highlight(lang)
        self._language_label = QtW.QLabel(lang.title())
        font = QtGui.QFont(MonospaceFontFamily)
        font.setPointSize(8)
        self._language_label.setFont(font)
        self._language_label.setFixedHeight(14)
        self._language_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._draggable_area = QDraggableArea()
        self._draggable_area.setFixedSize(14, 20)
        self._draggable_area.dragged.connect(self._drag_event)

        _layout = QtW.QVBoxLayout(self)
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.setSpacing(1)
        _layout.addWidget(self._text_edit)

        _footer_layout = QtW.QHBoxLayout()
        _footer_layout.setContentsMargins(1, 1, 1, 1)
        _footer_layout.addWidget(self._draggable_area)
        _footer_layout.addWidget(self._language_label)
        _layout.addLayout(_footer_layout)

        self._output_widget = None
        # NOTE: It seems that the byte content of QImage will be garbage collected
        # if we don't keep a reference to it.
        self._qimages: list[QtGui.QImage] = []
        if cell.outputs:
            output_widget = QIpynbOutput()
            _layout.addWidget(output_widget)
            for output in cell.outputs:
                if isinstance(output, ipynb.IpynbStreamOutput):
                    output_widget.append_text(output.get_text_plain())
                elif isinstance(output, ipynb.IpynbErrorOutput):
                    output_widget.append_html(output.get_html())
                elif isinstance(output, ipynb.IpynbDisplayDataOutput):
                    if (img := output.get_image()) is not None:
                        qimg = ndarray_to_qimage(img)
                        output_widget.append_image(qimg)
                        self._qimages.append(qimg)
                    elif html := output.get_text_html():
                        output_widget.append_html(html)
                    elif text := output.get_text_plain():
                        output_widget.append_text(text)

            self._output_widget = output_widget

        self._text_edit.textChanged.connect(self._on_text_changed)
        self._height_for_font = self._text_edit.fontMetrics().height()

    def _on_text_changed(self):
        nblocks = self._text_edit.blockCount()
        height = (self._height_for_font + 4) * min(nblocks, 10)
        if self._output_widget:
            height += self._output_widget.height()
        self.setFixedHeight(height + 40)

    def text(self) -> str:
        return self._text_edit.toPlainText()

    def _drag_event(self):
        cursor = self._text_edit.textCursor()
        font = self._text_edit.font()
        model = WidgetDataModel(
            value=self.text(),
            type=StandardType.TEXT,
            metadata=TextMeta(
                language=self._language_label.text().lower(),
                selection=(cursor.selectionStart(), cursor.selectionEnd()),
                font_family=font.family(),
                font_size=font.pointSizeF(),
            ),
        )
        ipynb_edit = self._ipynb_edit_ref()
        if ipynb_edit is not None:
            ipynb_edit._dragging_index = ipynb_edit._cell_widgets.index(self)
        drag_model(model, desc="Cell", source=ipynb_edit, text=model.value)

    def dragEnterEvent(self, a0):
        ipynb_edit = self._ipynb_edit_ref()
        if ipynb_edit is None or not ipynb_edit.is_editable():
            a0.ignore()
            return
        if model := _drag.get_dragging_model():
            if model.type == StandardType.TEXT:
                a0.accept()
                return
        a0.ignore()
        return

    def dropEvent(self, a0):
        if model := _drag.drop():
            ipynb_edit = self._ipynb_edit_ref()
            insert_idx = ipynb_edit._cell_widgets.index(self)
            if a0.pos().y() > self.rect().center().y():
                insert_idx += 1
            data_model = model.data_model()
            if a0.source() is ipynb_edit and ipynb_edit._dragging_index is not None:
                # move cell
                ipynb_edit.delete_cell(ipynb_edit._dragging_index)
                outputs = ipynb_edit._cell_widgets[insert_idx]._ipynb_cell.outputs
                if ipynb_edit._dragging_index < insert_idx:
                    insert_idx -= 1
                cell = ipynb.IpynbCell(
                    source=data_model.value,
                    cell_type="code",
                    outputs=outputs.copy(),
                )
            else:
                cell = ipynb.IpynbCell(source=data_model.value, cell_type="code")
            ipynb_edit.insert_cell(insert_idx, cell)


class QIpynbControl(QtW.QWidget):
    def __init__(self, parent: QIpynbEdit):
        super().__init__(parent)
        self._ipynb_edit = parent
        self._insert_cell_btn = QtW.QPushButton("+ Code")
        self._insert_cell_btn.clicked.connect(self._insert_code)
        self._insert_cell_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._insert_md_btn = QtW.QPushButton("+ Markdown")
        self._insert_md_btn.clicked.connect(self._insert_md)
        self._insert_md_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._delete_cell_btn = QtW.QPushButton("Delete")
        self._delete_cell_btn.clicked.connect(self._delete_cell)
        self._delete_cell_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._clear_outputs_btn = QtW.QPushButton("Clear Outputs")
        self._clear_outputs_btn.clicked.connect(self._clear_outputs)
        self._clear_outputs_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(QtW.QWidget())  # spacer
        layout.addWidget(self._insert_cell_btn)
        layout.addWidget(self._insert_md_btn)
        layout.addWidget(self._delete_cell_btn)

    def _insert_code(self):
        return self._insert_impl("code")

    def _insert_md(self):
        return self._insert_impl("markdown")

    def _delete_cell(self):
        idx = self._ipynb_edit.current_index()
        if idx != -1:
            self._ipynb_edit.delete_cell(idx)

    def _insert_impl(self, cell_type: str):
        idx = self._ipynb_edit.current_index()
        if idx == -1:
            idx = len(self._ipynb_edit._cell_widgets)
        cell = ipynb.IpynbCell(cell_type=cell_type)
        self._ipynb_edit.insert_cell(idx + 1, cell)

    def _clear_outputs(self):
        for widget in self._ipynb_edit._cell_widgets:
            if widget._output_widget is not None:
                widget._output_widget.clear()
                widget._qimages.clear()
                widget.setParent(None)
                widget.deleteLater()
            widget._ipynb_cell.outputs = []


class QIpynbOutput(QtW.QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.setStyleSheet(
            "QIpynbOutput { border: 1px solid gray; margin-left: 10px; }"
        )
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        font = QtGui.QFont(MonospaceFontFamily, 10)
        self.setFont(font)
        self.setFixedHeight(0)
        self._max_height = 400

        @self.customContextMenuRequested.connect
        def rightClickContextMenu(point):
            menu = self._make_contextmenu(point)
            if menu:
                menu.exec(self.mapToGlobal(point))

    def append_text(self, text: str):
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.insertPlainText(text)
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        if self.height() < self._max_height:
            font_height = self.fontMetrics().height() + 8
            new_height = self.height() + len(text.splitlines()) * font_height
            self.setFixedHeight(min(new_height, self._max_height))

    def append_html(self, html: str):
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.insertHtml(html)
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        if self.height() < self._max_height:
            font_height = self.fontMetrics().height() + 8
            new_height = self.height() + html.count("<br>") * font_height
            self.setFixedHeight(min(new_height, self._max_height))

    def append_image(self, qimage: QtGui.QImage):
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        cursor = self.textCursor()
        cursor.insertImage(qimage)
        self.insertPlainText("\n")
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        if self.height() < self._max_height:
            new_height = self.height() + qimage.height() + 16
            self.setFixedHeight(min(new_height, self._max_height))

    def _make_contextmenu(self, pos: QtCore.QPoint):
        """Reimplemented to return a custom context menu for images."""
        format = self.cursorForPosition(pos).charFormat()
        if name := format.stringProperty(QtGui.QTextFormat.Property.ImageName):
            menu = QtW.QMenu(self)
            menu.addAction("Copy Image", lambda: self._copy_image(name))
            menu.addAction("Save Image As...", lambda: self._save_image(name))
            return menu
        return None

    def _copy_image(self, name):
        image = self._get_image(name)
        if image is None:
            raise ValueError("Image not found")
        return QtW.QApplication.clipboard().setImage(image)

    def _save_image(self, name):
        """Shows a save dialog for the ImageResource with 'name'."""
        image = self._get_image(name)
        if image is None:
            raise ValueError("Image not found")
        dialog = QtW.QFileDialog(self, "Save Image")
        dialog.setAcceptMode(QtW.QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix("png")
        dialog.setNameFilter("PNG file (*.png)")
        if dialog.exec_():
            filename = dialog.selectedFiles()[0]
            image.save(filename, "PNG")
        return None

    def _get_image(self, name: str) -> QtGui.QImage | None:
        """Returns the QImage stored as the ImageResource with 'name'."""
        if document := self.document():
            image = document.resource(
                QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(name)
            )
            return image
        return None
