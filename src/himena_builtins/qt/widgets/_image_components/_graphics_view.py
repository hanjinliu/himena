from __future__ import annotations

import logging
import math
from typing import Iterable
import numpy as np
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from himena.types import Size

from ._base import QBaseGraphicsView, QBaseGraphicsScene
from ._roi_items import (
    QPointRoi,
    QPointsRoi,
    QPolygonRoi,
    QRoi,
    QLineRoi,
    QRectangleRoi,
    QEllipseRoi,
    QRotatedRectangleRoi,
    QSegmentedLineRoi,
    ROI_MODES,
    MouseMode,
)
from ._handles import QHandleRect, RoiSelectionHandles
from ._scale_bar import QScaleBarItem
from himena_builtins.qt.widgets._image_components import _mouse_events as _me
from himena.qt import ndarray_to_qimage
from himena.widgets import set_status_tip, get_clipboard, set_clipboard

_LOGGER = logging.getLogger(__name__)


class QImageGraphicsWidget(QtW.QGraphicsWidget):
    def __init__(self, parent=None, additive: bool = False):
        super().__init__(parent)
        self._img: np.ndarray = np.zeros((0, 0))
        self._qimage = QtGui.QImage()
        self._smoothing = False
        self.set_additive(additive)

    def set_image(self, img: np.ndarray):
        """Set a (colored) image to display."""
        qimg = ndarray_to_qimage(img)
        self._img = img
        self._qimage = qimg
        self.update()

    def set_additive(self, additive: bool):
        if additive:
            self._comp_mode = QtGui.QPainter.CompositionMode.CompositionMode_Plus
        else:
            self._comp_mode = QtGui.QPainter.CompositionMode.CompositionMode_SourceOver

    def setSmoothingEnabled(self, enabled):
        self._smoothing = enabled
        self.update()

    def initPainter(self, painter: QtGui.QPainter):
        painter.setCompositionMode(self._comp_mode)
        painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform, self._smoothing
        )

    def paint(self, painter, option, widget=None):
        if self._qimage.isNull():
            return

        self.initPainter(painter)
        bounding_rect = self.boundingRect()
        painter.drawImage(bounding_rect, self._qimage)
        is_light_bg = (
            self.scene().views()[0].backgroundBrush().color().lightness() > 128
        )
        if is_light_bg:
            pen = QtGui.QPen(QtGui.QColor(19, 19, 19), 1)
        else:
            pen = QtGui.QPen(QtGui.QColor(236, 236, 236), 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawRect(bounding_rect)

    def boundingRect(self):
        height, width = self._img.shape[:2]
        return QtCore.QRectF(0, 0, width, height)


class QRoiLabels(QtW.QGraphicsItem):
    """Item that shows labels for ROIs in the paint method"""

    def __init__(self, view: QImageGraphicsView):
        super().__init__()
        self._view = view
        self._show_labels = False
        self._font = QtGui.QFont("Arial", 10)
        self._bounding_rect = QtCore.QRectF(0, 0, 0, 0)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtW.QStyleOptionGraphicsItem,
        widget: QtW.QWidget,
    ):
        if not self._show_labels:
            return
        if not self._view._is_rois_visible:
            return
        scale = self.scene().views()[0].transform().m11()
        self._font.setPointSizeF(9 / scale)
        painter.setFont(self._font)
        metrics = QtGui.QFontMetricsF(self._font)
        for ith, roi in enumerate(self._view._roi_items):
            pos = self.mapToScene(roi.boundingRect().center())
            roi_label = roi.label() or str(ith)
            width = metrics.width(roi_label)
            height = metrics.height()
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 0), 1))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
            rect = QtCore.QRectF(
                pos.x() - width / 2, pos.y() - height / 2, width, height
            )
            painter.drawRect(rect.adjusted(-0.3, 0, 0.3, 0))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            painter.drawText(rect, roi_label)

    def boundingRect(self):
        return self._bounding_rect

    def set_bounding_rect(self, rect: QtCore.QRectF):
        self._bounding_rect = QtCore.QRectF(rect)
        self.update()


class QImageGraphicsView(QBaseGraphicsView):
    roi_added = QtCore.Signal(QRoi)
    roi_removed = QtCore.Signal(int)
    roi_visibility_changed = QtCore.Signal(bool)
    mode_changed = QtCore.Signal(MouseMode)
    hovered = QtCore.Signal(QtCore.QPointF)
    geometry_changed = QtCore.Signal(QtCore.QRectF)
    array_updated = QtCore.Signal(int, object)

    Mode = MouseMode

    def __init__(self, roi_visible: bool = False, roi_pen: QtGui.QPen | None = None):
        super().__init__()
        ### Attributes ###
        self._roi_items: list[QRoi] = []
        self._current_roi_item: QRoi | None = None
        self._is_current_roi_item_not_registered = False
        self._roi_pen = roi_pen or QtGui.QPen(QtGui.QColor(225, 225, 0), 3)
        self._roi_pen.setCosmetic(True)
        self._mode = MouseMode.PAN_ZOOM
        self._last_mode_before_key_hold = MouseMode.PAN_ZOOM
        self._mouse_event_handler = _me.PanZoomMouseEvents(self)
        self._is_drawing_multipoints = False
        self._is_rois_visible = roi_visible
        self._selection_handles = RoiSelectionHandles(self)
        self._initialized = False
        self._image_widgets: list[QImageGraphicsWidget] = []
        self.switch_mode(MouseMode.PAN_ZOOM)
        self._qroi_labels = self.addItem(QRoiLabels(self))
        self._qroi_labels.setZValue(10000)
        self._scale_bar_widget = self.addItem(QScaleBarItem(self))
        self._scale_bar_widget.setZValue(10000)
        self._scale_bar_widget.setVisible(False)
        self.geometry_changed.connect(self._scale_bar_widget.update_rect)
        self._stick_to_grid = False
        self.array_updated.connect(self._on_array_updated)

    def add_image_layer(self, additive: bool = False):
        self._image_widgets.append(
            self.addItem(QImageGraphicsWidget(additive=additive))
        )
        brect = self._image_widgets[0].boundingRect()
        self.scene().setSceneRect(brect)

    def set_n_images(self, num: int):
        if num < 1:
            raise ValueError("Number of images must be at least 1.")
        for _ in range(num - len(self._image_widgets)):
            additive = len(self._image_widgets) > 0
            self.add_image_layer(additive=additive)
        for _ in range(len(self._image_widgets) - num):
            widget = self._image_widgets.pop()
            self.scene().removeItem(widget)
            widget.deleteLater()

    def set_show_rois(self, show: bool):
        self._is_rois_visible = show
        for item in self._roi_items:
            item.setVisible(show)
        self._qroi_labels.update()
        self.roi_visibility_changed.emit(show)

    def set_show_labels(self, show: bool):
        self._qroi_labels._show_labels = show
        self._qroi_labels.update()

    def set_array(self, idx: int, img: np.ndarray | None):
        """Set an image to display."""
        # NOTE: image must be ready for conversion to QImage (uint8, mono or RGB)
        self.array_updated.emit(idx, img)

    def select_image(self):
        """Add a selection ROI to the entire image."""
        ny, nx = self._image_widgets[0]._img.shape[:2]
        self.remove_current_item(reason="Ctrl+A")
        self.set_current_roi(QRectangleRoi(0, 0, nx, ny).withPen(self._roi_pen))
        self._selection_handles.connect_rect(self._current_roi_item)
        return None

    def _on_array_updated(self, idx: int, img: np.ndarray | None):
        if idx >= len(self._image_widgets):
            return  # this happens when the number of channels decreased
        widget = self._image_widgets[idx]
        if img is None:
            widget.setVisible(False)
        else:
            widget.set_image(img)
            widget.setVisible(True)
        for widget in self._image_widgets:
            if widget.isVisible():
                self._qroi_labels.set_bounding_rect(widget.boundingRect())
                self._scale_bar_widget.set_bounding_rect(widget.boundingRect())
                break

    def set_image_blending(self, opaque: list[bool]):
        is_first = True
        for img, is_opaque in zip(self._image_widgets, opaque):
            if is_opaque and is_first:
                is_first = False
                img.set_additive(False)
            else:
                img.set_additive(True)

    def set_stick_to_grid(self, stick: bool):
        self._stick_to_grid = stick

    def clear_rois(self):
        scene = self.scene()
        for item in self._roi_items:
            scene.removeItem(item)
        self._roi_items.clear()
        if not self._is_current_roi_item_not_registered:
            self.remove_current_item(reason="clear all ROIs")

    def remove_rois(self, rois: Iterable[QRoi]):
        """Remove Qt ROIs from the view."""
        for roi in rois:
            if roi in self._roi_items:
                self._roi_items.remove(roi)
                self.scene().removeItem(roi)

    def extend_qrois(self, rois: Iterable[QRoi], current_roi: QRoi | None = None):
        """Set Qt ROIs to display."""
        for roi in rois:
            self.scene().addItem(roi)
            roi.setVisible(self._is_rois_visible)
            self._roi_items.append(roi)
            if roi is current_roi:
                self.select_item(
                    roi, is_registered_roi=not self._is_current_roi_item_not_registered
                )

    def mode(self) -> MouseMode:
        return self._mode

    def set_mode(self, mode: MouseMode):
        self._mode = mode
        _LOGGER.info("Mode changed to %r", mode)
        if mode in ROI_MODES:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            if mode is MouseMode.ROI_POINT:
                self._mouse_event_handler = _me.PointRoiMouseEvents(self)
            elif mode is MouseMode.ROI_POINTS:
                self._mouse_event_handler = _me.PointsRoiMouseEvents(self)
            elif mode is MouseMode.ROI_LINE:
                self._mouse_event_handler = _me.LineRoiMouseEvents(self)
            elif mode is MouseMode.ROI_RECTANGLE:
                self._mouse_event_handler = _me.RectangleRoiMouseEvents(self)
            elif mode is MouseMode.ROI_ELLIPSE:
                self._mouse_event_handler = _me.EllipseRoiMouseEvents(self)
            elif mode is MouseMode.ROI_POLYGON:
                self._mouse_event_handler = _me.PolygonRoiMouseEvents(self)
            elif mode is MouseMode.ROI_SEGMENTED_LINE:
                self._mouse_event_handler = _me.SegmentedLineRoiMouseEvents(self)
            elif mode is MouseMode.ROI_ROTATED_RECTANGLE:
                self._mouse_event_handler = _me.RotatedRectangleRoiMouseEvents(self)

        elif mode is MouseMode.SELECT:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            self._mouse_event_handler = _me.SelectMouseEvents(self)
        elif mode is MouseMode.PAN_ZOOM:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            self._mouse_event_handler = _me.PanZoomMouseEvents(self)
        self.mode_changed.emit(mode)

    def switch_mode(self, mode: MouseMode):
        self.set_mode(mode)
        self._last_mode_before_key_hold = mode
        set_status_tip(f"Mouse mode: {mode.name}", duration=1)

    def setSmoothing(self, enabled: bool):
        """Enable/disable image smoothing."""
        for im in self._image_widgets:
            im.setSmoothingEnabled(enabled)

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()

    def resize_event(self, old_size: Size, new_size: Size):
        """Process the resize event."""
        if (w_new := new_size.width) < 10 or (h_new := new_size.height) < 10:
            return
        if (w_old := old_size.width) == 0 or (h_old := old_size.height) == 0:
            ratio = 1.0
        else:
            ratio = math.sqrt(w_new / w_old * h_new / h_old)

        self.scale_and_update_handles(ratio)
        self._inform_scale()
        if not self._initialized:
            self.initialize()

    def showEvent(self, event):
        self.initialize()
        return super().showEvent(event)

    def initialize(self):
        if self._initialized:
            return
        if len(self._image_widgets) == 0:
            return
        first = self._image_widgets[0]
        rect = first.boundingRect()
        if (size := max(rect.width(), rect.height())) <= 0:
            return
        factor = 1 / size
        self.scale_and_update_handles(factor)
        self.centerOn(rect.center())
        self._initialized = True

    def _inform_scale(self):
        set_status_tip(f"Zoom factor: {self.transform().m11():.3%}", duration=0.7)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        dy = event.angleDelta().y()
        self._wheel_event(dy)
        return None  # NOTE: don't call super().wheelEvent(event)

    def _wheel_event(self, dy: int):
        factor = 1.1
        if dy > 0:
            zoom_factor = factor
        else:
            zoom_factor = 1 / factor
        self.scale_and_update_handles(zoom_factor)
        self._inform_scale()

    def scale_and_update_handles(self, factor: float):
        """Scale the view and update the selection handle sizes."""
        if len(self._image_widgets) > 0:
            image_size = self._image_widgets[0]._qimage.size()
            length = min(image_size.width(), image_size.height())
            new_scale = self.transform().m11() * factor
            if length * new_scale < 1 or new_scale > 1000:
                # too small or too large, do not zoom
                return
        if factor > 0:
            self.scale(factor, factor)
        tr = self.transform()
        self._selection_handles.update_handle_size(tr.m11())
        self.geometry_changed.emit(self.sceneRect())

    def auto_range(self):
        scene_rect = self.sceneRect()
        self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
        return None

    def remove_current_item(self, remove_from_list: bool = False, reason: str = ""):
        """Remove current ROI item.

        Parameters
        ----------
        remove_from_list : bool, optional
            If True, remove the item from the list of ROIs, otherwise just remove it
            from the scene.
        reason : str, optional
            Only used for logging.
        """
        if self._current_roi_item is not None:
            if not self._is_rois_visible:
                self._current_roi_item.setVisible(False)
            if remove_from_list:
                self.remove_item(self._current_roi_item)
            else:
                if self._is_current_roi_item_not_registered:
                    self.scene().removeItem(self._current_roi_item)
            self._selection_handles.clear_handles()
            self._current_roi_item = None
            _LOGGER.debug(
                "remove_current_item(remove_from_list=%r, reason=%r)",
                remove_from_list,
                reason,
            )

    def remove_item(self, item: QRoi):
        self.scene().removeItem(item)
        if not (
            item is self._current_roi_item and self._is_current_roi_item_not_registered
        ):
            idx = self._roi_items.index(item)
            del self._roi_items[idx]
            self.roi_removed.emit(idx)
        self._qroi_labels.update()

    def select_item(
        self,
        item: QtW.QGraphicsItem | None,
        is_registered_roi: bool = False,
    ):
        """Select the item during selection mode.

        Parameters
        ----------
        item : QGraphicsItem or None
            The item to select. If None, deselect the current item.
        is_registered_roi : bool, optional
            If True, the `item` is a considered as a registered ROI. This parameter is
            ususally used to select ROIs from the ROI list widget.
        """
        if item is not self._current_roi_item:
            self.remove_current_item(reason="deselect")
        if item is not None:
            if isinstance(item, QLineRoi):
                self._selection_handles.connect_line(item)
            elif isinstance(item, (QRectangleRoi, QEllipseRoi)):
                self._selection_handles.connect_rect(item)
            elif isinstance(item, (QPolygonRoi, QSegmentedLineRoi)):
                self._selection_handles.connect_path(item)
            elif isinstance(item, QPointsRoi):
                self._selection_handles.connect_points(item)
            elif isinstance(item, QPointRoi):
                self._selection_handles.connect_point(item)
            elif isinstance(item, QRotatedRectangleRoi):
                self._selection_handles.connect_rotated_rect(item)
            self._is_current_roi_item_not_registered = not is_registered_roi
        if isinstance(item, QRoi):
            self._current_roi_item = item
            item.setVisible(True)
            _LOGGER.debug("Item selected: %r", type(item).__name__)

    def select_item_at(self, pos: QtCore.QPointF) -> QRoi | None:
        """Select the item at the given position."""
        item_clicked = None
        is_registered = False
        if self._current_roi_item and self._current_roi_item.contains(pos):
            item_clicked = self._current_roi_item
            is_registered = not self._is_current_roi_item_not_registered
        elif self._is_rois_visible:
            for item in reversed(self._roi_items):
                if item.contains(pos):
                    item_clicked = item
                    is_registered = True
                    break
        self.select_item(item_clicked, is_registered_roi=is_registered)
        return item_clicked

    def _pos_to_tuple(self, pos: QtCore.QPointF) -> tuple[float, float]:
        if self._stick_to_grid:
            return int(round(pos.x())), int(round(pos.y()))
        return pos.x(), pos.y()

    def keyPressEvent(self, event):
        _key = event.key()
        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if _key == Qt.Key.Key_Up:
                if item := self._current_roi_item:
                    item.translate(0, -1)
                    return
            elif _key == Qt.Key.Key_Down:
                if item := self._current_roi_item:
                    item.translate(0, 1)
                    return
            elif _key == Qt.Key.Key_Left:
                if item := self._current_roi_item:
                    item.translate(-1, 0)
                    return
            elif _key == Qt.Key.Key_Right:
                if item := self._current_roi_item:
                    item.translate(1, 0)
                    return
        return super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        # Store the position of the mouse when the button is pressed
        if isinstance(item_under_cursor := self.itemAt(event.pos()), QHandleRect):
            # prioritize the handle mouse event
            self.scene().setGrabSource(item_under_cursor)
            return super().mousePressEvent(event)
        self.scene().setGrabSource(self)
        if event.button() == Qt.MouseButton.RightButton:
            pass
        else:
            self._mouse_event_handler.pressed(event)
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        # Move the image using the mouse
        if event.button() == Qt.MouseButton.NoButton:
            self.hovered.emit(self.mapToScene(event.pos()))
        elif event.buttons() & Qt.MouseButton.LeftButton:
            if (
                self._mouse_event_handler._pos_drag_start is None
                or self._mouse_event_handler._pos_drag_prev is None
                or self.scene().grabSource() is not self
            ):
                return super().mouseMoveEvent(event)
        self._mouse_event_handler.moved(event)
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_event_handler.released(event)
        elif event.button() == Qt.MouseButton.RightButton:
            if item := self.select_item_at(self.mapToScene(event.pos())):
                menu = self._make_menu_for_roi(item)
                menu.exec(event.globalPos())
            else:
                menu = self._make_menu_for_view()
                menu.exec(event.globalPos())
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        self._mouse_event_handler.double_clicked(event)
        return super().mouseDoubleClickEvent(event)

    def move_items_by(self, dx: int, dy: int):
        """Translate items."""
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
        self.geometry_changed.emit(self.sceneRect())

    def set_current_roi(self, item: QtW.QGraphicsItem):
        self._current_roi_item = item
        self._is_current_roi_item_not_registered = True
        # To avoid the automatic translation of the scene visible region during drawing
        # ROIs, reset the scene rect after adding the item
        rect = self.scene().sceneRect()
        self.scene().addItem(item)
        self.scene().setSceneRect(rect)
        _LOGGER.info(f"Set current ROI item to {item}")

    def add_current_roi(self):
        """Register the current ROI item."""
        if item := self._current_roi_item:
            self._is_current_roi_item_not_registered = False
            if len(self._roi_items) > 0 and self._roi_items[-1] is item:
                # do not add the same item
                return
            _LOGGER.info(f"Added ROI item {item}")
            self._selection_handles.finish_drawing_polygon()
            self._roi_items.append(item)
            self._qroi_labels.update()
            self.roi_added.emit(item)

    def standard_key_press(self, _key: Qt.Key):
        if _key == Qt.Key.Key_Space:
            self._last_mode_before_key_hold = self.mode()
            self.set_mode(MouseMode.PAN_ZOOM)
        elif _key == Qt.Key.Key_R:
            if self.mode() is MouseMode.ROI_RECTANGLE:
                self.switch_mode(MouseMode.ROI_ROTATED_RECTANGLE)
            else:
                self.switch_mode(MouseMode.ROI_RECTANGLE)
        elif _key == Qt.Key.Key_E:
            self.switch_mode(MouseMode.ROI_ELLIPSE)
        elif _key == Qt.Key.Key_P:
            # switch similar modes in turn
            if self.mode() is MouseMode.ROI_POINT:
                self.switch_mode(MouseMode.ROI_POINTS)
            else:
                self.switch_mode(MouseMode.ROI_POINT)
        elif _key == Qt.Key.Key_L:
            if self.mode() is MouseMode.ROI_LINE:
                self.switch_mode(MouseMode.ROI_SEGMENTED_LINE)
            else:
                self.switch_mode(MouseMode.ROI_LINE)
        elif _key == Qt.Key.Key_G:
            self.switch_mode(MouseMode.ROI_POLYGON)
        elif _key == Qt.Key.Key_S:
            self.switch_mode(MouseMode.SELECT)
        elif _key == Qt.Key.Key_Z:
            self.switch_mode(MouseMode.PAN_ZOOM)
        elif _key == Qt.Key.Key_T:
            self.add_current_roi()
        elif _key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.remove_current_item(remove_from_list=True, reason="delete key")
        elif _key == Qt.Key.Key_V:
            self.set_show_rois(not self._is_rois_visible)

    def standard_ctrl_key_press(self, key: Qt.Key):
        if key == Qt.Key.Key_A:
            self.select_image()
        elif key == Qt.Key.Key_X:
            if self._current_roi_item is not None:
                item = self._current_roi_item.copy()
                self.remove_current_item(remove_from_list=True, reason="Ctrl+X")
                set_clipboard(text=str(item), internal_data=item)
        elif key == Qt.Key.Key_C:
            self._copy_current_roi()
        elif key == Qt.Key.Key_V:
            self._paste_roi()
        elif key == Qt.Key.Key_D:  # duplicate ROI
            if self._current_roi_item is not None:
                # item = self._current_roi_item.copy()
                # set_clipboard(text=str(item), internal_data=item)
                self._copy_current_roi()
                self._paste_roi()

    def _copy_current_roi(self):
        if self._current_roi_item is not None:
            if self._is_current_roi_item_not_registered:
                self.add_current_roi()
            item = self._current_roi_item.copy()
            set_clipboard(text=str(item), internal_data=item)

    def _paste_roi(self):
        model = get_clipboard()
        item = model.internal_data
        if not isinstance(item, QRoi):
            return
        sx, sy = self.transform().m11(), self.transform().m22()
        delta = QtCore.QPointF(4 / sx, 4 / sy)
        dx, dy = self._pos_to_tuple(delta)
        item.translate(max(dx, 1), max(dy, 1))
        self.set_current_roi(item)
        self.add_current_roi()
        self._selection_handles.connect_rect(item)
        set_clipboard(model.with_internal_data(item.copy()))  # needed for Ctrl+V x2

    def _make_menu_for_roi(self, roi: QRoi):
        menu = QtW.QMenu(self)
        action = menu.addAction("Copy ROI")
        action.triggered.connect(
            lambda: set_clipboard(text=str(roi), internal_data=roi.copy())
        )
        action = menu.addAction("Delete ROI")
        action.triggered.connect(lambda: self.remove_item(roi))
        return menu

    def _make_menu_for_view(self):
        menu = QtW.QMenu(self)
        action = menu.addAction("Copy view to clipboard")
        action.triggered.connect(
            lambda: QtW.QApplication.clipboard().setImage(self.grab().toImage())
        )
        return menu
