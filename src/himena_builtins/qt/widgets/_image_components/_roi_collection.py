from __future__ import annotations
import weakref
from functools import singledispatch
from qtpy import QtWidgets as QtW, QtCore, QtGui
from typing import Iterator, TYPE_CHECKING

from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena.standards import roi
from himena.consts import StandardType
from himena.standards.model_meta import ImageRoisMeta
from himena.types import WidgetDataModel, DragDataModel
from himena.qt import drag_model
from himena_builtins.qt.widgets._image_components import _roi_items
from himena_builtins.qt.widgets._dragarea import QDraggableArea

if TYPE_CHECKING:
    from himena_builtins.qt.widgets.image import QImageView


@singledispatch
def _roi_to_qroi(r: roi.RoiModel) -> _roi_items.QRoi:
    raise ValueError(f"Unsupported ROI type: {type(r)}")


@_roi_to_qroi.register
def _(r: roi.LineRoi) -> _roi_items.QRoi:
    return _roi_items.QLineRoi(r.x1 + 0.5, r.y1 + 0.5, r.x2 + 0.5, r.y2 + 0.5)


@_roi_to_qroi.register
def _(r: roi.RectangleRoi) -> _roi_items.QRoi:
    return _roi_items.QRectangleRoi(r.x, r.y, r.width, r.height)


@_roi_to_qroi.register
def _(r: roi.EllipseRoi) -> _roi_items.QRoi:
    return _roi_items.QEllipseRoi(r.x, r.y, r.width, r.height)


@_roi_to_qroi.register
def _(r: roi.SegmentedLineRoi) -> _roi_items.QRoi:
    return _roi_items.QSegmentedLineRoi(r.xs + 0.5, r.ys + 0.5)


@_roi_to_qroi.register
def _(r: roi.PolygonRoi) -> _roi_items.QRoi:
    return _roi_items.QPolygonRoi(r.xs + 0.5, r.ys + 0.5)


@_roi_to_qroi.register
def _(r: roi.RotatedRectangleRoi) -> _roi_items.QRoi:
    xstart, ystart = r.start
    xend, yend = r.end
    return _roi_items.QRotatedRectangleRoi(
        QtCore.QPointF(xstart + 0.5, ystart + 0.5),
        QtCore.QPointF(xend + 0.5, yend + 0.5),
        width=r.width,
    )


@_roi_to_qroi.register
def _(r: roi.PointRoi2D) -> _roi_items.QRoi:
    return _roi_items.QPointRoi(r.x + 0.5, r.y + 0.5)


@_roi_to_qroi.register
def _(r: roi.PointsRoi2D) -> _roi_items.QRoi:
    return _roi_items.QPointsRoi(r.xs + 0.5, r.ys + 0.5)


def from_standard_roi(r: roi.RoiModel, pen: QtGui.QPen) -> _roi_items.QRoi:
    """Convert a standard ROI to a QRoi."""
    out = _roi_to_qroi(r)
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
            if isinstance(r, roi.RoiND):
                self.add(r.indices, from_standard_roi(r, self._pen))
        return self

    def to_standard_roi_list(
        self,
        selections: list[int] | None = None,
    ) -> roi.RoiListModel:
        if selections is None:
            all_rois = self._rois
        else:
            all_rois = [self._rois[i] for i in selections]
        return roi.RoiListModel(rois=[roi.toRoi(indices) for indices, roi in all_rois])

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

    def set_selections(self, selections: list[int]):
        sel_model = self._list_view.selectionModel()
        sel_model.clear()
        model = self._list_view.model()
        for i in selections:
            sel_model.select(
                model.index(i, 0), QtCore.QItemSelectionModel.SelectionFlag.Select
            )

    def current_row(self) -> int | None:
        index = self._list_view.currentIndex()
        if index.isValid():
            return index.row()
        return None

    def selections(self) -> list[int]:
        return [idx.row() for idx in self._list_view.selectionModel().selectedIndexes()]

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


class QRoiCollection(QSimpleRoiCollection):
    """Object to store and manage multiple ROIs in nD images."""

    show_rois_changed = QtCore.Signal(bool)
    show_labels_changed = QtCore.Signal(bool)
    roi_item_clicked = QtCore.Signal(tuple, _roi_items.QRoi)
    key_pressed = QtCore.Signal(QtGui.QKeyEvent)
    key_released = QtCore.Signal(QtGui.QKeyEvent)

    def __init__(self, parent: QImageView):
        super().__init__(parent)
        self._image_view_ref = weakref.ref(parent)
        self._list_view.clicked.connect(self._on_item_clicked)
        self._list_view.key_pressed.connect(self.key_pressed)
        self._list_view.key_released.connect(self.key_released)

        self.layout().addWidget(
            self._list_view, 100, alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._dragarea = QDraggableArea()
        self._dragarea.setToolTip("Drag the image ROIs")
        self._dragarea.setFixedSize(14, 14)
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
        _btn_layout.addWidget(
            self._dragarea, alignment=QtCore.Qt.AlignmentFlag.AlignLeft
        )
        _btn_layout.addWidget(QtW.QWidget(), 100)
        _btn_layout.addWidget(
            self._add_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        _btn_layout.addWidget(
            self._remove_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self.layout().addLayout(_btn_layout)
        self._dragarea.dragged.connect(self._on_dragged)
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

    def _on_dragged(self):
        img_view = self._image_view_ref()
        if img_view._original_title is not None:
            title = f"ROIs or {img_view._original_title}"
        else:
            title = "ROIs"

        def _data_model_getter():
            axes = img_view._dims_slider._to_image_axes()
            roilist = roi.RoiListModel(
                rois=[r.toRoi(indices) for indices, r in self._rois]
            )
            return WidgetDataModel(
                value=roilist,
                type=StandardType.IMAGE_ROIS,
                title=title,
                metadata=ImageRoisMeta(axes=axes, selections=self.selections()),
            )

        model = DragDataModel(getter=_data_model_getter, type=StandardType.IMAGE_ROIS)
        _s = "" if len(self._rois) == 1 else "s"
        return drag_model(model, desc=f"{len(self._rois)} ROI{_s}", source=img_view)


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
        self.setDragEnabled(True)
        self.setMouseTracking(True)
        self._hover_drag_indicator = QDraggableArea(self)
        self._hover_drag_indicator.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
        )
        self._hover_drag_indicator.setFixedSize(14, 14)
        self._hover_drag_indicator.hide()
        self._hover_drag_indicator.dragged.connect(self._on_drag)
        self._indicator_index: int = -1

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

    def mouseMoveEvent(self, e):
        if e.button() == QtCore.Qt.MouseButton.NoButton:
            # hover
            index = self.indexAt(e.pos())
            if index.isValid():
                self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                index_rect = self.rectForIndex(index)
                top_right = index_rect.topRight()
                top_right.setX(top_right.x() - 14)
                self._hover_drag_indicator.move(top_right)
                self._hover_drag_indicator.show()
                self._indicator_index = index.row()
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
                self._hover_drag_indicator.hide()
        return super().mouseMoveEvent(e)

    def leaveEvent(self, a0):
        self._hover_drag_indicator.hide()
        return super().leaveEvent(a0)

    def sizeHint(self):
        return QtCore.QSize(180, 900)  # set to a very large value to make it expanded

    def parent(self) -> QRoiCollection:
        return super().parent()

    def _on_drag(self) -> None:
        sels = self.parent().selections()
        if self._indicator_index not in sels:
            sels.append(self._indicator_index)
            index = self.model().index(self._indicator_index, 0)
            self.selectionModel().select(
                index, QtCore.QItemSelectionModel.SelectionFlag.Select
            )
        self.drag_requested.emit(sels)


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
