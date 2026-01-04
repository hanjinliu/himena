from __future__ import annotations

import math
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtPdfWidgets import QPdfView
from qtpy.QtPdf import QPdfDocument, QPdfSearchModel

from himena import WidgetDataModel
from himena.widgets import show_tooltip
from himena.qt._qlineedit import QIntLineEdit
from himena.qt._qfinderwidget import QFinderWidget
from himena.plugins import validate_protocol
from himena_builtins.qt.widgets._shared import spacer_widget


class QPdfViewer(QtW.QWidget):
    """A widget for displaying PDF files."""

    def __init__(self):
        super().__init__()
        self._pdf_view = _QPdfView(self)
        self._pdf_document = QPdfDocument(self)
        self._pdf_view.setDocument(self._pdf_document)
        self._pdf_view._search_model.setDocument(self._pdf_document)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._pdf_view)
        self._drag_start_pos: QtCore.QPoint | None = None
        self._control: QPdfViewControl | None = None
        self._finder: QFinderWidget | None = None

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        """Update the widget to display the PDF from the data model."""
        if not isinstance(_bytes := model.value, (bytes, bytearray)):
            raise TypeError("Expected bytes or bytearray for PDF data.")
        byte_array = QtCore.QByteArray(_bytes)
        buf = QtCore.QBuffer(byte_array)
        buf.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
        try:
            self._pdf_document.load(buf)
        finally:
            buf.close()

    @validate_protocol
    def control_widget(self) -> QPdfViewControl:
        if self._control is None:
            self._control = QPdfViewControl(self)
        return self._control

    @validate_protocol
    def size_hint(self):
        return 480, 520

    def set_page(self, page_number: int):
        """Set the current page to display."""
        self._pdf_view.pageNavigator().jump(page_number, QtCore.QPointF(0, 0))


class QPdfViewControl(QtW.QWidget):
    """A control widget for QPdfViewer to navigate pages and adjust zoom."""

    def __init__(self, view: QPdfViewer):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._spin_box_page = QIntLineEdit()
        self._spin_box_page.setMinimum(1)
        self._spin_box_page.setFixedWidth(40)
        self._spin_box_page.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._spin_box_zoom = QIntLineEdit()
        self._spin_box_zoom.setMinimum(1)
        self._spin_box_zoom.setMaximum(1000)
        self._spin_box_zoom.setFixedWidth(50)
        self._spin_box_zoom.setText("100")
        self._spin_box_zoom.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._label_max = QtW.QLabel()
        self._view = view
        view._pdf_view.page_changed.connect(self._on_page_changed)
        view._pdf_view.zoomFactorChanged.connect(self._on_zoom_changed)
        view._pdf_view.documentChanged.connect(self._on_document_changed)
        layout.addWidget(spacer_widget())
        layout.addWidget(QtW.QLabel("Zoom:"))
        layout.addWidget(self._spin_box_zoom)
        layout.addWidget(QtW.QLabel("%"))
        layout.addWidget(QtW.QLabel("Page:"))
        layout.addWidget(self._spin_box_page)
        layout.addWidget(self._label_max)
        self._spin_box_page.valueChanged.connect(self._on_spinbox_page_changed)
        self._spin_box_zoom.valueChanged.connect(self._on_spinbox_zoom_changed)
        self._on_document_changed()

    def _on_page_changed(self, page_number: int):
        self._spin_box_page.setText(str(page_number + 1))

    def _on_zoom_changed(self, zoom: float):
        self._spin_box_zoom.setText(str(int(zoom * 100)))

    def _on_document_changed(self):
        pmax = self._view._pdf_document.pageCount()
        self._spin_box_page.blockSignals(True)
        try:
            self._spin_box_page.setMaximum(max(1, pmax))
            self._spin_box_page.setText("1")
            self._label_max.setText(f"/ {pmax}")
        finally:
            self._spin_box_page.blockSignals(False)

    def _on_spinbox_page_changed(self, value: str):
        if value == "":
            return
        self._view.set_page(int(value) - 1)

    def _on_spinbox_zoom_changed(self, value: str):
        if value == "":
            return
        zoom = int(value) / 100
        self._spin_box_zoom.blockSignals(True)
        try:
            self._view._pdf_view.setZoomFactor(zoom)
        finally:
            self._spin_box_zoom.blockSignals(False)


class _QPdfView(QPdfView):
    page_changed = QtCore.Signal(int)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._drag_start_pos: QtCore.QPoint | None = None
        self.setPageMode(QPdfView.PageMode.MultiPage)
        self.setPageSpacing(12)
        self.pageNavigator().currentPageChanged.connect(self.page_changed)
        self._search_model = QPdfSearchModel(self)
        self.setSearchModel(self._search_model)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handle mouse wheel events for zooming."""
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            new_zoom = self._zoom_by_delta(delta)
            show_tooltip(f"Zoom: {new_zoom:.1%}", duration=1, behavior="until_move")
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press events for dragging."""
        if event.buttons() & QtCore.Qt.MouseButton.MiddleButton:
            self._drag_start_pos = event.pos()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse move events for dragging."""
        if (
            self._drag_start_pos is not None
            and event.buttons() & QtCore.Qt.MouseButton.MiddleButton
        ):
            delta = event.pos() - self._drag_start_pos
            if scrollbar_h := self.horizontalScrollBar():
                scrollbar_h.setValue(scrollbar_h.value() - delta.x())
            if scrollbar_v := self.verticalScrollBar():
                scrollbar_v.setValue(scrollbar_v.value() - delta.y())
            self._drag_start_pos = event.pos()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse release events."""
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._drag_start_pos = None
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, a0):
        """Handle key press events for page navigation."""
        if a0.key() == QtCore.Qt.Key.Key_Plus:
            self._zoom_by_delta(120)
        elif a0.key() == QtCore.Qt.Key.Key_Minus:
            self._zoom_by_delta(-120)
        else:
            super().keyPressEvent(a0)

    def _zoom_by_delta(self, delta) -> float:
        if delta > 0:
            zoom_factor = 1.1
            rounder = math.ceil
        else:
            zoom_factor = 1 / 1.1
            rounder = math.floor
        new_zoom = self.zoomFactor() * zoom_factor
        if new_zoom > 0.2:
            new_zoom = rounder(new_zoom * 20) / 20  # Round to nearest 0.05
        else:
            new_zoom = rounder(new_zoom * 100) / 100  # Round to nearest 0.01
        new_zoom = max(new_zoom, 0.01)
        self.setZoomFactor(new_zoom)
        return new_zoom
