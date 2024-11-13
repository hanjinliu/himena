from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy import QtCore
from himena.model_meta import TableMeta
from himena.qt._qfinderwidget import QTableFinderWidget


class QTableBase(QtW.QTableView):
    def __init__(self):
        super().__init__()
        self.horizontalHeader().setFixedHeight(18)
        self.verticalHeader().setDefaultSectionSize(22)
        self.horizontalHeader().setDefaultSectionSize(75)
        self._finder_widget: QTableFinderWidget | None = None

        # scroll by pixel
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        # scroll bar policy
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)

    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    def is_editable(self) -> bool:
        return self.editTriggers() != QtW.QAbstractItemView.EditTrigger.NoEditTriggers

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QTableFinderWidget(self)
        self._finder_widget.show()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)

    def _prep_table_meta(self) -> TableMeta:
        qselections = self.selectionModel().selection()
        selections = []
        for qselection in qselections:
            r = qselection.top(), qselection.bottom() + 1
            c = qselection.left(), qselection.right() + 1
            selections.append((r, c))
        index = self.currentIndex()
        return TableMeta(
            current_position=(index.row(), index.column()),
            selections=selections,
        )
