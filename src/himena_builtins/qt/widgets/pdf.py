from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore

from himena import WidgetDataModel
from himena.plugins import validate_protocol
from superqt import QLabeledSlider


class QPdfViewer(QtW.QWidget):
    """A widget for displaying PDF files."""

    def __init__(self, parent: QtW.QWidget | None = None):
        from qtpy.QtPdf import QPdfDocument
        from qtpy.QtPdfWidgets import QPdfView

        super().__init__(parent)
        self._pdf_view = QPdfView(self)
        self._pdf_document = QPdfDocument(self)
        self._pdf_view.setDocument(self._pdf_document)
        self._page_slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._page_slider.valueChanged.connect(self.set_page)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._page_slider)
        layout.addWidget(self._pdf_view)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        """Update the widget to display the PDF from the data model."""
        self._pdf_document.load(str(model.value))
        self._pdf_view.setZoomMode(self._pdf_view.ZoomMode.FitToWidth)
        self._page_slider.setRange(0, self._pdf_document.pageCount() - 1)
        self._page_slider.setValue(0)

    @validate_protocol
    def size_hint(self):
        return 480, 520

    def set_page(self, page_number: int):
        """Set the current page to display."""
        if 0 <= page_number < self._pdf_document.pageCount():
            navigation = self._pdf_view.pageNavigator()
            navigation.jump(page_number, QtCore.QPointF())
