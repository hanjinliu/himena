from __future__ import annotations
import weakref
from functools import singledispatch
import numpy as np
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from typing import Iterator, TYPE_CHECKING, Sequence
from superqt import QToggleSwitch
from magicgui.widgets import Container

from himena.standards import roi
from himena.consts import StandardType
from himena.qt import drag_command
from himena.qt.magicgui import get_type_map
from himena.utils.ndobject import NDObjectCollection
from himena_builtins.qt.widgets._image_components import _roi_items
from himena_builtins.qt.widgets._dragarea import QDraggableArea

if TYPE_CHECKING:
    from typing import Self
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
    roi = _roi_items.QPolygonRoi(r.xs + 0.5, r.ys + 0.5)
    path = roi.path()
    path.closeSubpath()
    roi.setPath(path)
    return roi


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
    roi_update_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._qroi_list = NDObjectCollection[_roi_items.QRoi]()
        self._pen = QtGui.QPen(QtGui.QColor(238, 238, 0), 2)
        self._pen.setCosmetic(True)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._list_view = QRoiListView(self)

        layout.addWidget(self._list_view, 100, alignment=Qt.AlignmentFlag.AlignTop)
        self._list_view.drag_requested.connect(self.drag_requested.emit)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({len(self)} ROIs)"

    def layout(self) -> QtW.QVBoxLayout:
        return super().layout()

    def extend_from_standard_roi_list(
        self,
        rois: NDObjectCollection[roi.RoiModel],
    ) -> Self:
        """Extend the collection from a list of himena standard ROIs."""
        qrois = np.fromiter(
            (from_standard_roi(r, self._pen) for r in rois),
            dtype=np.object_,
        )
        self.extend(
            NDObjectCollection[_roi_items.QRoi](
                items=qrois,
                indices=rois.indices,
                axis_names=rois.axis_names,
            )
        )
        return self

    def to_standard_roi_list(
        self,
        selections: list[int] | None = None,
    ) -> NDObjectCollection[roi.RoiModel]:
        if selections is None:
            all_rois = self._qroi_list
        else:
            all_rois = self._qroi_list.filter_by_selection(selections)
        return all_rois.map_elements(lambda qroi: qroi.toRoi(), into=roi.RoiListModel)

    def add(self, indices: Indices, roi: _roi_items.QRoi):
        """Add a ROI on the given slice."""
        self._list_view.model().beginInsertRows(
            QtCore.QModelIndex(), len(self._qroi_list), len(self._qroi_list)
        )
        self._qroi_list.add_item(indices, roi)
        self._list_view.model().endInsertRows()

    def extend(self, other: NDObjectCollection[_roi_items.QRoi]):
        self._list_view.model().beginInsertRows(
            QtCore.QModelIndex(),
            len(self._qroi_list),
            len(self._qroi_list) + len(other),
        )
        self._qroi_list.extend(other)
        self._list_view.model().endInsertRows()

    def clear(self):
        self._list_view.model().beginResetModel()
        self._qroi_list.clear()
        self._list_view.model().endResetModel()

    def set_selections(self, selections: list[int]):
        sel_model = self._list_view.selectionModel()
        sel_model.clear()
        model = self._list_view.model()
        for i in selections:
            sel_model.select(
                model.index(i, 0), QtCore.QItemSelectionModel.SelectionFlag.Select
            )

    def selections(self) -> list[int]:
        """List of selected indices"""
        return [idx.row() for idx in self._list_view.selectionModel().selectedIndexes()]

    def __getitem__(self, key: int) -> _roi_items.QRoi:
        return self._qroi_list[key]

    def count(self) -> int:
        return len(self._qroi_list)

    __len__ = count

    def __iter__(self) -> Iterator[_roi_items.QRoi]:
        yield from self._qroi_list

    def get_rois_on_slice(self, indices: tuple[int, ...]) -> Sequence[_roi_items.QRoi]:
        """Return a list of ROIs on the given slice."""
        out = self._qroi_list.filter_by_indices(indices).items
        return out

    def pop_roi_in_slice(self, indices: Indices, ith: int) -> _roi_items.QRoi:
        """Pop the `index`-th ROI in the slice `indices`."""
        mask = self._qroi_list.mask_by_indices(indices)
        if mask is None:
            index_total = ith
        else:
            index_total = np.where(mask)[0][ith]
        qindex = self._list_view.model().index(index_total)
        self._list_view.model().beginRemoveRows(qindex, index_total, index_total)
        roi = self._qroi_list.pop(index_total)
        self._list_view.model().endRemoveRows()
        self._list_view.update()
        return roi

    def pop_rois(self, indices: list[int]):
        sl = np.ones(self.count(), dtype=bool)
        sl[indices] = False
        self._list_view.model().beginRemoveRows(QtCore.QModelIndex(), 0, len(sl) - 1)
        self._qroi_list = self._qroi_list.filter_by_selection(sl)
        self._list_view.model().endRemoveRows()

    def flatten_roi(self, indices: int | list[int]) -> None:
        return self.flatten_roi_along(indices, slice(None))

    def flatten_roi_along(self, indices: int | list[int], axis) -> None:
        self._qroi_list.indices[indices, axis] = -1
        return None

    def move_roi(self, indices: int | list[int], new_dims: tuple[int, ...]) -> None:
        if not isinstance(indices, list):
            indices = [indices]
        for i in indices:
            self._qroi_list.indices[i, :] = new_dims
        self.roi_update_requested.emit()
        return None

    def remove_selected_rois(self):
        self.pop_rois(self.selections())
        self.roi_update_requested.emit()


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

        self.layout().addWidget(self._list_view, 100, Qt.AlignmentFlag.AlignTop)
        self._dragarea = QDraggableArea()
        self._dragarea.setToolTip("Drag the image ROIs")
        self._dragarea.setFixedSize(14, 14)
        self._add_btn = QtW.QPushButton("+")
        self._add_btn.setToolTip("Register current ROI to the list")
        self._add_btn.setFixedSize(14, 14)
        self._add_btn.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
        )
        self._add_btn.clicked.connect(parent._img_view.add_current_roi)
        self._remove_btn = QtW.QPushButton("-")
        self._remove_btn.setToolTip("Remove selected ROI from the list")
        self._remove_btn.setFixedSize(14, 14)
        self._remove_btn.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
        )
        _btn_layout = QtW.QHBoxLayout()
        _btn_layout.setContentsMargins(0, 0, 0, 0)
        _btn_layout.setSpacing(1)
        _btn_layout.addWidget(self._dragarea, alignment=Qt.AlignmentFlag.AlignLeft)
        _btn_layout.addWidget(QtW.QWidget(), 100)
        _btn_layout.addWidget(self._add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        _btn_layout.addWidget(self._remove_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addLayout(_btn_layout)
        self._dragarea.dragged.connect(self._on_dragged)
        self._roi_visible_btn = QToggleSwitch()
        self._roi_visible_btn.setText("Show ROIs")
        self._roi_visible_btn.setChecked(True)
        self._roi_labels_btn = QToggleSwitch()
        self._roi_labels_btn.setText("Labels")
        self._roi_labels_btn.setChecked(True)
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
            self._roi_visible_btn, alignment=Qt.AlignmentFlag.AlignBottom
        )
        self.layout().addWidget(
            self._roi_labels_btn, alignment=Qt.AlignmentFlag.AlignBottom
        )

        self.show_rois_changed.connect(parent._img_view.set_show_rois)
        self.show_labels_changed.connect(parent._img_view.set_show_labels)
        self.key_pressed.connect(parent.keyPressEvent)
        self.key_released.connect(parent.keyReleaseEvent)
        self.roi_item_clicked.connect(self._roi_item_clicked)
        self._add_btn.clicked.connect(parent._img_view.add_current_roi)
        self.drag_requested.connect(parent._on_drag_roi_requested)
        self._remove_btn.clicked.connect(self.remove_selected_rois)

        self._roi_visible_btn.toggled.connect(self._on_roi_visible_btn_clicked)
        self._roi_labels_btn.toggled.connect(self._on_roi_labels_btn_clicked)

        self.setToolTip("List of ROIs in the image")

    def _roi_item_clicked(self, indices: tuple[int, ...], qroi: _roi_items.QRoi):
        view = self._image_view_ref()
        if view is None:
            return

        # find the proper slider indices
        if (ninds := len(indices)) < (ndim_rem := view._dims_slider.count()):
            # this happens when the ROI is flattened
            if ninds > 0:
                higher_dims = ndim_rem - ninds
                indices_filled = view._dims_slider.value()[:higher_dims] + indices
                view._dims_slider.set_value_no_emit(indices_filled)
                view._slider_changed(view._dims_slider.value(), force_sync=True)
        else:
            view._dims_slider.set_value_no_emit(indices)
            view._slider_changed(view._dims_slider.value(), force_sync=True)

        # update selection in the image viewer
        view._img_view.select_item(qroi, is_registered_roi=True)

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
        if 0 <= r < len(self._qroi_list):
            qroi = self._qroi_list[r]
            indices = self._qroi_list.indices[r]
            self.roi_item_clicked.emit(tuple(indices), qroi)

    def _on_dragged(self):
        _s = "" if len(self._qroi_list) == 1 else "s"
        return drag_command(
            self._image_view_ref(),
            command_id="builtins:duplicate-rois",
            type=StandardType.ROIS,
            desc=f"{len(self._qroi_list)} ROI{_s}",
        )


class QRoiListView(QtW.QListView):
    # NOTE: list view usually has a focus. Key events have to be forwarded.
    key_pressed = QtCore.Signal(QtGui.QKeyEvent)
    key_released = QtCore.Signal(QtGui.QKeyEvent)
    drag_requested = QtCore.Signal(list)  # list[int] of selected indices

    def __init__(self, parent: QRoiCollection):
        super().__init__(parent)
        self.setModel(QRoiListModel(parent))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.EditKeyPressed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setDragEnabled(True)
        self.setMouseTracking(True)
        self._hover_drag_indicator = QDraggableArea(self)
        self._hover_drag_indicator.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._hover_drag_indicator.setFixedSize(14, 14)
        self._hover_drag_indicator.hide()
        self._hover_drag_indicator.dragged.connect(self._on_drag)
        self._indicator_index: int = -1

    def set_selection(self, indices: list[int]):
        """Set the selection of the list view."""
        self.clearSelection()
        for i in indices:
            index = self.model().index(i, 0)
            self.selectionModel().select(
                index, QtCore.QItemSelectionModel.SelectionFlag.Select
            )
        if len(indices) > 0:
            self.parent()._on_item_clicked(self.model().index(indices[0], 0))

    def _show_context_menu(self, point):
        index_under_cursor = self.indexAt(point)
        if not index_under_cursor.isValid():
            return
        menu = self._prep_context_menu(index_under_cursor)
        menu.exec(self.mapToGlobal(point))

    def _prep_context_menu(self, index: QtCore.QModelIndex):
        _qroi_list = self.parent()._qroi_list
        menu = QtW.QMenu(self)
        selected_indices = self.parent().selections()
        action_rename = menu.addAction("Rename", lambda: self.edit(index))
        action_rename.setToolTip("Rename the selected ROI")
        menu_flatten = menu.addMenu("Flatten Along ...")

        action_flatten = menu_flatten.addAction(
            "All axes", lambda: self.parent().flatten_roi(selected_indices)
        )
        menu_flatten.addSeparator()
        for i in range(_qroi_list.ndim):
            _action = menu_flatten.addAction(
                f"{i}: {_qroi_list.axis_names[i]}",
                lambda i=i: self.parent().flatten_roi_along(selected_indices, [i]),
            )
            _action.setToolTip(
                f"Flatten the selected ROI along {_qroi_list.axis_names[i]!r} axis"
            )
            if self.parent()._qroi_list.indices[index.row(), i] == -1:
                _action.setEnabled(False)  # already flattened
        action_flatten.setToolTip("Flatten the selected ROI into 2D")
        action_move = menu.addAction(
            "Move To ...",
            lambda: self._move_to(selected_indices),
        )
        action_move.setToolTip("Move the selected ROI to another dimension")
        action_delete = menu.addAction(
            "Delete", lambda: self.parent().remove_selected_rois()
        )
        action_delete.setToolTip("Delete the selected ROIs")
        return menu

    def _move_to(self, indices):
        if dims := self._select_dimensions_from_dialog():
            self.parent().move_roi(indices, dims)

    def _make_dialog(self, options: dict[str, dict]) -> tuple[QtW.QDialog, Container]:
        mgui_typemap = get_type_map()
        dialog = QtW.QDialog(self)
        dialog.setWindowTitle("Select dimensions")
        layout = QtW.QVBoxLayout(dialog)
        container = Container()
        container.margins = (0, 0, 0, 0)
        for name, each in options.items():
            annotation = each.pop("annotation", None)
            widget = mgui_typemap.create_widget(
                annotation=annotation,
                name=name,
                options=each,
            )
            container.append(widget)
        layout.addWidget(container.native)
        button_layout = QtW.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        ok_button = QtW.QPushButton("OK")
        cancel_button = QtW.QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        return dialog, container

    def _options_for_select_dimensions(self) -> dict[str, dict]:
        options = {}
        img_view = self.parent()._image_view_ref()
        if img_view is None:
            return None
        slider_dims = img_view._dims_slider.maximums()
        slider_values = list(img_view._dims_slider.value())
        for ith, axis in enumerate(self.parent()._qroi_list.axis_names):
            options[axis] = {
                "value": slider_values[ith],
                "annotation": int,
                "widget_type": "Slider",
                "min": 0,
                "max": slider_dims[ith],
            }
        return options

    def _select_dimensions_from_dialog(self) -> tuple[int, ...] | None:
        options = self._options_for_select_dimensions()
        dialog, container = self._make_dialog(options)
        if dialog.exec() == QtW.QDialog.DialogCode.Accepted:
            return tuple(each.value for each in container)
        else:
            return None

    def keyPressEvent(self, a0: QtGui.QKeyEvent):
        if a0.key() == Qt.Key.Key_F2:
            self.edit(self.currentIndex())
            return
        elif a0.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            return super().keyPressEvent(a0)
        self.key_pressed.emit(a0)

    def keyReleaseEvent(self, a0):
        self.key_released.emit(a0)
        return super().keyReleaseEvent(a0)

    def mouseMoveEvent(self, e):
        if e.button() == Qt.MouseButton.NoButton:
            # hover
            index = self.indexAt(e.pos())
            if index.isValid():
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                index_rect = self.rectForIndex(index)
                top_right = index_rect.topRight()
                top_right.setX(top_right.x() - 14)
                self._hover_drag_indicator.move(top_right)
                self._hover_drag_indicator.show()
                self._indicator_index = index.row()
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
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
    Qt.ItemFlag.ItemIsEnabled
    | Qt.ItemFlag.ItemIsSelectable
    | Qt.ItemFlag.ItemIsEditable
)


class QRoiListModel(QtCore.QAbstractListModel):
    """The list model used for displaying ROIs."""

    def __init__(self, col: QRoiCollection, parent=None):
        super().__init__(parent)
        self._col = col

    def rowCount(self, parent=None):
        return len(self._col)

    def data(self, index: QtCore.QModelIndex, role: int):
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            r = index.row()
            if 0 <= r < len(self._col):
                return self._col[r].label()
            return None
        elif role == Qt.ItemDataRole.DecorationRole:
            r = index.row()
            if 0 <= r < len(self._col):
                pixmap = QtGui.QPixmap(24, 24)
                pixmap.fill(Qt.GlobalColor.black)
                return self._col[r].makeThumbnail(pixmap).scaled(
                    12, 12, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )  # fmt: skip
        elif role == Qt.ItemDataRole.FontRole:
            font = self._col.font()
            font.setPointSize(10)
            if index == self._col._list_view.currentIndex():
                font.setBold(True)
            return font
        elif role == Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(80, 14)
        elif role == Qt.ItemDataRole.ToolTipRole:
            r = index.row()
            if 0 <= r < len(self._col):
                _indices = tuple(self._col._qroi_list.indices[r])
                _type = self._col._qroi_list[r]._roi_type()
                if len(_indices) > 0:
                    return f"{_type.title()} ROI on slice {_indices}"
                else:
                    return f"{_type.title()} ROI"
        return None

    def flags(self, index):
        return _FLAGS

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self._col._qroi_list[index.row()].set_label(value)
            return True
