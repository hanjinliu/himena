from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from typing import Iterator

from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena.standards import roi
from himena_builtins.qt.widgets._image_components import _roi_items
from himena.consts import StandardType
from himena.types import WidgetDataModel, DragDataModel
from himena.qt import drag_model


def from_standard_roi(r: roi.ImageRoi, pen: QtGui.QPen) -> _roi_items.QRoi:
    if isinstance(r, roi.LineRoi):
        out = _roi_items.QLineRoi(r.x1, r.y1, r.x2, r.y2)
    elif isinstance(r, roi.RectangleRoi):
        out = _roi_items.QRectangleRoi(r.x, r.y, r.width, r.height)
    elif isinstance(r, roi.EllipseRoi):
        out = _roi_items.QEllipseRoi(r.x, r.y, r.width, r.height)
    elif isinstance(r, roi.SegmentedLineRoi):
        out = _roi_items.QSegmentedLineRoi(r.xs, r.ys)
    elif isinstance(r, roi.PolygonRoi):
        out = _roi_items.QPolygonRoi(r.xs, r.ys)
    elif isinstance(r, roi.RotatedRectangleRoi):
        out = _roi_items.QRotatedRectangleRoi(
            QtCore.QPointF(*r.start), QtCore.QPointF(*r.end), r.width
        )
    elif isinstance(r, roi.PointRoi):
        out = _roi_items.QPointRoi(r.x, r.y)
    elif isinstance(r, roi.PointsRoi):
        out = _roi_items.QPointsRoi(r.xs, r.ys)
    else:
        raise ValueError(f"Unsupported ROI type: {type(r)}")
    return out.withPen(pen).withLabel(r.name)


Indices = tuple[int, ...]


class QSimpleRoiCollection(QtW.QWidget):
    drag_requested = QtCore.Signal(list)  # list[int] of selected indices

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rois: list[tuple[Indices, _roi_items.QRoi]] = []
        self._slice_cache: dict[Indices, list[_roi_items.QRoi]] = {}
        self._pen = QtGui.QPen(QtGui.QColor(238, 238, 0), 2)
        self._pen.setCosmetic(True)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._list_view = QRoiListView(self)

        layout.addWidget(
            self._list_view, 100, alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._list_view.drag_requested.connect(self.drag_requested.emit)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({len(self)} ROIs)"

    def layout(self) -> QtW.QVBoxLayout:
        return super().layout()

    def update_from_standard_roi_list(self, rois: roi.RoiListModel) -> QRoiCollection:
        for r in rois:
            if isinstance(r, roi.ImageRoiND):
                self.add(r.indices, from_standard_roi(r, self._pen))
        return self

    def to_standard_roi_list(self) -> roi.RoiListModel:
        return roi.RoiListModel(
            rois=[roi.toRoi(indices) for indices, roi in self._rois],
        )

    def add(self, indices: Indices, roi: _roi_items.QRoi):
        """Add a ROI on the given slice."""
        self._list_view.model().beginInsertRows(
            QtCore.QModelIndex(), len(self._rois), len(self._rois)
        )
        self._rois.append((indices, roi))
        self._cache_roi(indices, roi)
        self._list_view.model().endInsertRows()

    def _cache_roi(self, indices: Indices, roi: _roi_items.QRoi):
        if indices not in self._slice_cache:
            self._slice_cache[indices] = []
        self._slice_cache[indices].append(roi)

    def extend(self, other: QRoiCollection):
        for indices, r in other._rois:
            self.add(indices, r)

    def clear(self):
        self._list_view.model().beginResetModel()
        self._rois.clear()
        self._slice_cache.clear()
        self._list_view.model().endResetModel()

    def __getitem__(self, key: int) -> _roi_items.QRoi:
        return self._rois[key][1]

    def __len__(self) -> int:
        return len(self._rois)

    def __iter__(self) -> Iterator[_roi_items.QRoi]:
        for _, r in self._rois:
            return r

    def get_rois_on_slice(self, indices: tuple[int, ...]) -> list[_roi_items.QRoi]:
        """Return a list of ROIs on the given slice."""
        indices_to_collect = []
        for i in range(len(indices) + 1):  # append until get `()`
            indices_to_collect.append(indices[i:])
        out = []
        for idx in indices_to_collect:
            out.extend(self._slice_cache.get(idx, []))
        return out

    def pop_roi(self, indices: Indices, index: int) -> _roi_items.QRoi:
        qindex = self._list_view.model().index(index)
        self._list_view.model().beginRemoveRows(qindex, index, index)
        rois = self._slice_cache[indices]
        roi = rois.pop(index)
        self._rois.remove((indices, roi))
        self._list_view.model().endRemoveRows()
        return roi

    def flatten_roi(self, index: int) -> _roi_items.QRoi:
        indices, roi = self._rois[index]
        if len(indices) == 0:
            return roi
        self._rois[index] = ((), roi)
        self._slice_cache[indices].remove(roi)
        self._cache_roi((), roi)
        return roi

    def _run_drag_model(self, indices: list[int], source: QtW.QWidget | None = None):
        rois = [self._rois[i] for i in indices]

        def _data_model_getter():
            roilist = roi.RoiListModel(rois=[r.toRoi(indices) for indices, r in rois])
            return WidgetDataModel(value=roilist, type=StandardType.IMAGE_ROIS)

        model = DragDataModel(getter=_data_model_getter, type=StandardType.IMAGE_ROIS)
        _s = "" if len(rois) == 1 else "s"
        return drag_model(model, desc=f"{len(rois)} ROI{_s}", source=source)


class QRoiCollection(QSimpleRoiCollection):
    """Object to store and manage multiple ROIs in nD images."""

    show_rois_changed = QtCore.Signal(bool)
    show_labels_changed = QtCore.Signal(bool)
    roi_item_clicked = QtCore.Signal(tuple, _roi_items.QRoi)
    key_pressed = QtCore.Signal(QtGui.QKeyEvent)
    key_released = QtCore.Signal(QtGui.QKeyEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list_view.clicked.connect(self._on_item_clicked)
        self._list_view.key_pressed.connect(self.key_pressed)
        self._list_view.key_released.connect(self.key_released)

        self.layout().addWidget(
            self._list_view, 100, alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._add_btn = QtW.QPushButton("+")
        self._add_btn.setToolTip("Register current ROI to the list")
        self._add_btn.setFixedSize(14, 14)
        self._add_btn.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
        )
        self._remove_btn = QtW.QPushButton("-")
        self._remove_btn.setToolTip("Remove selected ROI from the list")
        self._remove_btn.setFixedSize(14, 14)
        self._remove_btn.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
        )
        _btn_layout = QtW.QHBoxLayout()
        _btn_layout.setContentsMargins(0, 0, 0, 0)
        _btn_layout.setSpacing(1)
        _btn_layout.addWidget(QtW.QWidget(), 100)
        _btn_layout.addWidget(
            self._add_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        _btn_layout.addWidget(
            self._remove_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self.layout().addLayout(_btn_layout)
        self._roi_visible_btn = QLabeledToggleSwitch()
        self._roi_visible_btn.setText("Show ROIs")
        self._roi_visible_btn.setChecked(False)
        self._roi_labels_btn = QLabeledToggleSwitch()
        self._roi_labels_btn.setText("Labels")
        self._roi_labels_btn.setChecked(False)
        self._roi_visible_btn.setSizePolicy(
            QtW.QSizePolicy(
                QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
            )
        )
        self._roi_labels_btn.setSizePolicy(
            QtW.QSizePolicy(
                QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
            )
        )
        self.layout().addWidget(
            self._roi_visible_btn, alignment=QtCore.Qt.AlignmentFlag.AlignBottom
        )
        self.layout().addWidget(
            self._roi_labels_btn, alignment=QtCore.Qt.AlignmentFlag.AlignBottom
        )

        self._roi_visible_btn.toggled.connect(self._on_roi_visible_btn_clicked)
        self._roi_labels_btn.toggled.connect(self._on_roi_labels_btn_clicked)

        self.setToolTip("List of ROIs in the image")

    def _on_roi_visible_btn_clicked(self, checked: bool):
        if self._roi_labels_btn.isChecked() and not checked:
            self._roi_labels_btn.setChecked(False)
        self.show_rois_changed.emit(checked)

    def _on_roi_labels_btn_clicked(self, checked: bool):
        if checked and not self._roi_visible_btn.isChecked():
            self._roi_visible_btn.setChecked(True)
        self.show_labels_changed.emit(checked)

    def _on_item_clicked(self, index: QtCore.QModelIndex):
        r = index.row()
        if 0 <= r < len(self._rois):
            indices, roi = self._rois[r]
            self.roi_item_clicked.emit(indices, roi)


def _is_drag_mouse_event(e: QtGui.QMouseEvent):
    return (
        e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        and e.buttons() & QtCore.Qt.MouseButton.LeftButton
    ) or e.buttons() & QtCore.Qt.MouseButton.MiddleButton


class QRoiListView(QtW.QListView):
    # NOTE: list view usually has a focus. Key events have to be forwarded.
    key_pressed = QtCore.Signal(QtGui.QKeyEvent)
    key_released = QtCore.Signal(QtGui.QKeyEvent)
    drag_requested = QtCore.Signal(list)  # list[int] of selected indices

    def __init__(self, parent: QRoiCollection):
        super().__init__(parent)
        self.setModel(QRoiListModel(parent))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.EditKeyPressed)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._is_dragging = False

    def _show_context_menu(self, point):
        index_under_cursor = self.indexAt(point)
        if not index_under_cursor.isValid():
            return
        menu = QtW.QMenu(self)
        action_rename = menu.addAction("Rename", lambda: self.edit(index_under_cursor))
        action_rename.setToolTip("Rename the selected ROI")
        action_flatten = menu.addAction(
            "Flatten", lambda: self.parent().flatten_roi(index_under_cursor.row())
        )
        action_flatten.setToolTip("Flatten the selected ROI into 2D")

        menu.exec(self.mapToGlobal(point))

    def keyPressEvent(self, a0: QtGui.QKeyEvent):
        if a0.key() == QtCore.Qt.Key.Key_F2:
            self.edit(self.currentIndex())
            return
        elif a0.key() in (QtCore.Qt.Key.Key_Up, QtCore.Qt.Key.Key_Down):
            return super().keyPressEvent(a0)
        self.key_pressed.emit(a0)
        return super().keyPressEvent(a0)

    def keyReleaseEvent(self, a0):
        self.key_released.emit(a0)
        return super().keyReleaseEvent(a0)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        return None

    def mouseMoveEvent(self, e):
        if self._is_dragging:
            return super().mouseMoveEvent(e)
        self._is_dragging = True
        if _is_drag_mouse_event(e):
            index = self.indexAt(e.pos())
            if not self.selectionModel().isSelected(index):
                self.selectionModel().select(
                    index, QtCore.QItemSelectionModel.SelectionFlag.Select
                )
            indices = [ind.row() for ind in self.selectedIndexes()]
            self.drag_requested.emit(indices)
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if not self._is_dragging:
            index = self.indexAt(e.pos())
            if not (e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
                self.clearSelection()
            if index.isValid():
                self.selectionModel().select(
                    index, QtCore.QItemSelectionModel.SelectionFlag.Toggle
                )
        self._is_dragging = False
        return super().mouseReleaseEvent(e)

    def sizeHint(self):
        return QtCore.QSize(180, 900)  # set to a very large value to make it expanded

    def parent(self) -> QRoiCollection:
        return super().parent()


_FLAGS = (
    QtCore.Qt.ItemFlag.ItemIsEnabled
    | QtCore.Qt.ItemFlag.ItemIsSelectable
    | QtCore.Qt.ItemFlag.ItemIsEditable
)


class QRoiListModel(QtCore.QAbstractListModel):
    """The list model used for displaying ROIs."""

    def __init__(self, col: QRoiCollection, parent=None):
        super().__init__(parent)
        self._col = col

    def rowCount(self, parent):
        return len(self._col)

    def data(self, index: QtCore.QModelIndex, role: int):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            r = index.row()
            if 0 <= r < len(self._col):
                return self._col[r].label()
            return None
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            r = index.row()
            if 0 <= r < len(self._col):
                pixmap = QtGui.QPixmap(24, 24)
                pixmap.fill(QtCore.Qt.GlobalColor.black)
                return self._col[r].makeThumbnail(pixmap).scaled(
                    12, 12, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )  # fmt: skip
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            font = self._col.font()
            font.setPointSize(10)
            if index == self._col._list_view.currentIndex():
                font.setBold(True)
            return font
        elif role == QtCore.Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(80, 14)
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            r = index.row()
            if 0 <= r < len(self._col):
                _indices, _roi = self._col._rois[r]
                _type = _roi._roi_type()
                if len(_indices) > 0:
                    return f"{_type.title()} ROI on slice {_indices}"
                else:
                    return f"{_type.title()} ROI"
        return None

    def flags(self, index):
        return _FLAGS

    def setData(self, index, value, role):
        if role == QtCore.Qt.ItemDataRole.EditRole:
            self._col._rois[index.row()][1].set_label(value)
            return True
