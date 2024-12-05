from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from enum import Enum, auto
from cmap import Colormap
import numpy as np
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from ._base import QBaseGraphicsView, QBaseGraphicsScene
from ._roi_items import (
    QPointRoi,
    QPointsRoi,
    QPolygonRoi,
    QRoi,
    QLineRoi,
    QRectangleRoi,
    QEllipseRoi,
    QSegmentedLineRoi,
    from_standard_roi,
)
from ._handles import QHandleRect, RoiSelectionHandles
from himena.qt._utils import ndarray_to_qimage

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class Mode(Enum):
    """Mouse interaction modes for the image graphics view."""

    SELECT = auto()
    PAN_ZOOM = auto()
    ROI_RECTANGLE = auto()
    ROI_ELLIPSE = auto()
    ROI_POINT = auto()
    ROI_POINTS = auto()
    ROI_POLYGON = auto()
    ROI_SEGMENTED_LINE = auto()
    ROI_LINE = auto()


SIMPLE_ROI_MODES = frozenset({Mode.ROI_RECTANGLE, Mode.ROI_ELLIPSE, Mode.ROI_POINT, Mode.ROI_LINE})  # fmt: skip
MULTIPOINT_ROI_MODES = frozenset({Mode.ROI_POINTS, Mode.ROI_POLYGON, Mode.ROI_SEGMENTED_LINE})  # fmt: skip
ROI_MODES = SIMPLE_ROI_MODES | MULTIPOINT_ROI_MODES
MULTIPOINT_ROI_CLASSES = (QPolygonRoi, QSegmentedLineRoi, QPointsRoi)


class QImageGraphicsWidget(QtW.QGraphicsWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._img: np.ndarray = np.zeros((0, 0))
        self._qimage = QtGui.QImage()
        self._smoothing = False
        self._opacity = 255
        self._colormap = Colormap("gray")

    def set_image(self, img: np.ndarray):
        """Set a (colored) image to display."""
        qimg = ndarray_to_qimage(img, self._opacity)
        self._img = img
        self._qimage = qimg
        self.update()

    def setSmoothingEnabled(self, enabled):
        self._smoothing = enabled
        self.update()

    def paint(self, painter, option, widget=None):
        if self._qimage.isNull():
            return
        painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform, self._smoothing
        )
        bounding_rect = self.boundingRect()
        painter.drawImage(bounding_rect, self._qimage)
        is_light_bg = self.scene().backgroundBrush().color().lightness() > 128
        if is_light_bg:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 1))
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
        painter.drawRect(bounding_rect)

    def boundingRect(self):
        height, width = self._img.shape[:2]
        return QtCore.QRectF(0, 0, width, height)


class QImageGraphicsView(QBaseGraphicsView):
    roi_added = QtCore.Signal(QRoi)
    roi_removed = QtCore.Signal(int)
    mode_changed = QtCore.Signal(Mode)
    hovered = QtCore.Signal(QtCore.QPointF)

    Mode = Mode

    def __init__(self):
        ### Attributes ###
        self._pos_drag_start: QtCore.QPoint | None = None
        self._pos_drag_prev: QtCore.QPoint | None = None
        self._roi_items: list[QtW.QGraphicsItem] = []
        self._current_roi_item: QRoi | None = None
        self._is_current_roi_item_not_registered = False
        self._roi_pen = QtGui.QPen(QtGui.QColor(225, 225, 0), 3)
        self._roi_pen.setCosmetic(True)
        self._mode = Mode.PAN_ZOOM
        self._last_mode_before_key_hold = Mode.PAN_ZOOM
        self._is_drawing_multipoints = False
        self._is_rois_visible = False
        self._selection_handles = RoiSelectionHandles(self)
        self._initialized = False

        super().__init__()
        self._image_widget = self.addItem(QImageGraphicsWidget())
        self.switch_mode(Mode.PAN_ZOOM)

    def set_array(self, img: np.ndarray, clear_rois: bool = True):
        """Set an image to display."""
        # NOTE: image must be ready for conversion to QImage (uint8, mono or RGB)
        self._image_widget.set_image(img)
        # ROI is stored in the parent widget.
        if clear_rois:
            scene = self.scene()
            for item in self._roi_items:
                scene.removeItem(item)
            self._roi_items.clear()
            if not self._is_current_roi_item_not_registered:
                self.remove_current_item()

    def set_rois(self, rois: list):
        """Set ROIs to display."""
        for roi in rois:
            qroi = from_standard_roi(roi, self._roi_pen)
            self.scene().addItem(qroi)
            qroi.setVisible(self._is_rois_visible)
            self._roi_items.append(qroi)

    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode):
        self._mode = mode
        if mode in ROI_MODES:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif mode is Mode.SELECT:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        elif mode is Mode.PAN_ZOOM:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.mode_changed.emit(mode)

    def switch_mode(self, mode: Mode):
        self.set_mode(mode)
        self._last_mode_before_key_hold = mode

    def setSmoothing(self, enabled: bool):
        # Enable or disable pixmap smoothing
        self._image_widget.setSmoothingEnabled(enabled)

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        # Dynamically resize the image to keep the current zoom factor
        old_size = event.oldSize()
        new_size = event.size()
        ratio = np.sqrt(
            new_size.width() / old_size.width() * new_size.height() / old_size.height()
        )
        self.scale_and_update_handles(ratio)
        return super().resizeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        if not (event.spontaneous() and self._initialized):
            rect = self._image_widget.boundingRect()
            factor = 1 / max(rect.width(), rect.height())
            self.scale_and_update_handles(factor)
            self.centerOn(rect.center())
            self._initialized = True

    def wheelEvent(self, event):
        # Zoom in/out using the mouse wheel
        factor = 1.1

        if event.angleDelta().y() > 0:
            zoom_factor = factor
        else:
            zoom_factor = 1 / factor
        self.scale_and_update_handles(zoom_factor)
        return super().wheelEvent(event)

    def scale_and_update_handles(self, factor: float):
        """Scale the view and update the selection handle sizes."""
        self.scale(factor, factor)
        tr = self.transform()
        self._selection_handles.update_handle_size(tr.m11())

    def auto_range(self):
        return self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def remove_current_item(self, remove_from_list: bool = False):
        if self._current_roi_item is not None:
            if not self._is_rois_visible:
                self._current_roi_item.setVisible(False)
            if remove_from_list:
                self.scene().removeItem(self._current_roi_item)
                if not self._is_current_roi_item_not_registered:
                    idx = self._roi_items.index(self._current_roi_item)
                    del self._roi_items[idx]
                    self.roi_removed.emit(idx)
            else:
                if self._is_current_roi_item_not_registered:
                    self.scene().removeItem(self._current_roi_item)
            self._selection_handles.clear_handles()
            self._current_roi_item = None

    def select_item(self, item: QtW.QGraphicsItem | None):
        """Select the item during selection mode."""
        if item is None:
            self.remove_current_item()
        elif isinstance(item, QLineRoi):
            self._selection_handles.connect_line(item)
        elif isinstance(item, (QRectangleRoi, QEllipseRoi)):
            self._selection_handles.connect_rect(item)
        elif isinstance(item, (QPolygonRoi, QSegmentedLineRoi)):
            self._selection_handles.connect_path(item)
        elif isinstance(item, QPointsRoi):
            self._selection_handles.connect_points(item)
        if isinstance(item, QRoi):
            self._current_roi_item = item
        self._is_current_roi_item_not_registered = False

    def select_item_at(self, pos: QtCore.QPointF):
        """Select the item at the given position."""
        item_clicked = None
        if self._current_roi_item and self._current_roi_item.contains(pos):
            item_clicked = self._current_roi_item
        elif self._is_rois_visible:
            for item in reversed(self._roi_items):
                if item.contains(pos):
                    item_clicked = item
                    break
        self.select_item(item_clicked)

    def mousePressEvent(self, event):
        # Store the position of the mouse when the button is pressed
        if isinstance(item_under_cursor := self.itemAt(event.pos()), QHandleRect):
            # prioritize the handle mouse event
            self.scene().setGrabSource(item_under_cursor)
            return super().mousePressEvent(event)
        self._pos_drag_start = event.pos()
        self._pos_drag_prev = self._pos_drag_start
        if self._mode in ROI_MODES:
            grabbing = self.scene().grabSource()
            if grabbing is not None and grabbing is not self:
                return super().mousePressEvent(event)
            self.scene().setGrabSource(self)
            if self._mode in MULTIPOINT_ROI_MODES:
                if not self._selection_handles.is_drawing_polygon():
                    is_poly = isinstance(
                        self._current_roi_item, (QPolygonRoi, QSegmentedLineRoi)
                    )
                    self.remove_current_item()
                    if is_poly:
                        # clear current drawing
                        self.select_item(None)
                        return super().mousePressEvent(event)
                self._selection_handles.start_drawing_polygon()
                return super().mousePressEvent(event)
            self.remove_current_item()
            p = self.mapToScene(self._pos_drag_start)
            if self._mode is Mode.ROI_LINE:
                self.set_current_roi(
                    QLineRoi(p.x(), p.y(), p.x(), p.y()).withPen(self._roi_pen)
                )
                self._selection_handles.connect_line(self._current_roi_item)
            elif self._mode is Mode.ROI_RECTANGLE:
                self.set_current_roi(
                    QRectangleRoi(p.x(), p.y(), 0, 0).withPen(self._roi_pen)
                )
                self._selection_handles.connect_rect(self._current_roi_item)
            elif self._mode is Mode.ROI_ELLIPSE:
                self.set_current_roi(
                    QEllipseRoi(p.x(), p.y(), 0, 0).withPen(self._roi_pen)
                )
                self._selection_handles.connect_rect(self._current_roi_item)
            elif self._mode is Mode.ROI_POINT:
                pass

        elif self._mode is Mode.SELECT:
            self.select_item_at(self.mapToScene(event.pos()))
            self.scene().setGrabSource(self)
        elif self._mode is Mode.PAN_ZOOM:
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            self.scene().setGrabSource(self)

        return super().mousePressEvent(event)

    def _mouse_move_pan_zoom(self, event: QtGui.QMouseEvent):
        delta = event.pos() - self._pos_drag_prev
        self.move_items_by(delta.x(), delta.y())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        # Move the image using the mouse
        pos = self.mapToScene(event.pos())
        if event.buttons() == Qt.MouseButton.NoButton:
            self.hovered.emit(pos)
            if (
                self._mode in MULTIPOINT_ROI_MODES
                and self._selection_handles.is_drawing_polygon()
                and isinstance(self._current_roi_item, (QPolygonRoi, QSegmentedLineRoi))
            ):
                # update the last point of the polygon
                if self._selection_handles._is_last_vertex_added:
                    self._selection_handles._is_last_vertex_added = False
                    self._current_roi_item.add_point(pos)
                else:
                    num = self._current_roi_item.count()
                    if num > 1:
                        self._current_roi_item.update_point(num - 1, pos)
        elif event.buttons() & Qt.MouseButton.LeftButton:
            pos = self.mapToScene(event.pos())
            if (
                self._pos_drag_start is None
                or self._pos_drag_prev is None
                or self.scene().grabSource() is not self
            ):
                return super().mouseMoveEvent(event)
            pos0 = self.mapToScene(self._pos_drag_start)
            if self._mode is Mode.PAN_ZOOM:
                self._mouse_move_pan_zoom(event)
            elif self._mode is Mode.ROI_LINE:
                if isinstance(item := self._current_roi_item, QLineRoi):
                    item.setLine(pos0.x(), pos0.y(), pos.x(), pos.y())
            elif self._mode in (Mode.ROI_RECTANGLE, Mode.ROI_ELLIPSE):
                if isinstance(self._current_roi_item, (QRectangleRoi, QEllipseRoi)):
                    x0, x1 = sorted([pos.x(), pos0.x()])
                    y0, y1 = sorted([pos.y(), pos0.y()])
                    self._current_roi_item.setRect(x0, y0, x1 - x0, y1 - y0)
            elif self._mode is Mode.SELECT:
                if item := self._current_roi_item:
                    delta = pos - self.mapToScene(self._pos_drag_prev)
                    item.translate(delta.x(), delta.y())
                else:
                    # just forward to the pan-zoom mode
                    self._mouse_move_pan_zoom(event)
            elif self._mode in (Mode.ROI_POINTS, Mode.ROI_POINT):
                self._mouse_move_pan_zoom(event)

            self._pos_drag_prev = event.pos()
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if self._pos_drag_start == event.pos():
            p0 = self.mapToScene(self._pos_drag_start)
            # mouse click
            if (
                self._mode in MULTIPOINT_ROI_MODES
                and self._selection_handles.is_drawing_polygon()
            ):
                if not isinstance(self._current_roi_item, MULTIPOINT_ROI_CLASSES):
                    x1, y1 = p0.x(), p0.y()
                    if self._mode is Mode.ROI_POLYGON:
                        self.set_current_roi(
                            QPolygonRoi([x1], [y1]).withPen(self._roi_pen)
                        )
                        self._selection_handles.connect_path(self._current_roi_item)
                    elif self._mode is Mode.ROI_SEGMENTED_LINE:
                        self.set_current_roi(
                            QSegmentedLineRoi([x1], [y1]).withPen(self._roi_pen)
                        )
                        self._selection_handles.connect_path(self._current_roi_item)
                    elif self._mode is Mode.ROI_POINTS:
                        self.set_current_roi(
                            QPointsRoi([x1], [y1]).withPen(self._roi_pen)
                        )
                        self._selection_handles.connect_points(self._current_roi_item)
                    else:
                        raise NotImplementedError
                elif isinstance(
                    self._current_roi_item, (QPolygonRoi, QSegmentedLineRoi, QPointsRoi)
                ):
                    _LOGGER.info(f"Added point {self._pos_drag_start} to {self._mode}")
                    self._current_roi_item.add_point(p0)
                self._selection_handles._is_last_vertex_added = True
            elif self._mode is Mode.ROI_POINT:
                self.set_current_roi(QPointRoi(p0.x(), p0.y()).withPen(self._roi_pen))
                self._selection_handles.connect_point(self._current_roi_item)
        if self._mode is Mode.PAN_ZOOM:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.scene().setGrabSource(None)
        self._pos_drag_prev = None
        self._pos_drag_start = None
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if self._mode in {Mode.ROI_LINE, Mode.ROI_RECTANGLE, Mode.ROI_ELLIPSE}:
            self.remove_current_item()
        elif self._mode is Mode.PAN_ZOOM:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._selection_handles.finish_drawing_polygon()
        return super().mouseDoubleClickEvent(event)

    def move_items_by(self, dx: float, dy: float):
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)

    def set_current_roi(self, item: QtW.QGraphicsItem):
        self._current_roi_item = item
        self._is_current_roi_item_not_registered = True
        self.scene().addItem(item)
        _LOGGER.info(f"Set current ROI item to {item}")

    def add_current_roi(self):
        if item := self._current_roi_item:
            self._is_current_roi_item_not_registered = False
            if len(self._roi_items) > 0 and self._roi_items[-1] is item:
                # do not add the same item
                return
            _LOGGER.info(f"Added ROI item {item}")
            self._roi_items.append(item)
            self.roi_added.emit(item)

    def toggle_roi_list_visibility(self):
        self._is_rois_visible = not self._is_rois_visible
        for item in self._roi_items:
            item.setVisible(self._is_rois_visible)

    def keyPressEvent(self, event: QtGui.QKeyEvent | None) -> None:
        if event is None:
            return super().keyPressEvent(event)
        _mods = event.modifiers()
        _key = event.key()
        if _mods == Qt.KeyboardModifier.NoModifier:
            if _key == Qt.Key.Key_Space:
                self._last_mode_before_key_hold = self._mode
                self.set_mode(Mode.PAN_ZOOM)
            elif _key == Qt.Key.Key_Up:
                if item := self._current_roi_item:
                    item.translate(0, -1)
                    self._selection_handles.translate(0, -1)
            elif _key == Qt.Key.Key_Down:
                if item := self._current_roi_item:
                    item.translate(0, 1)
                    self._selection_handles.translate(0, 1)
            elif _key == Qt.Key.Key_Left:
                if item := self._current_roi_item:
                    item.translate(-1, 0)
                    self._selection_handles.translate(-1, 0)
            elif _key == Qt.Key.Key_Right:
                if item := self._current_roi_item:
                    item.translate(1, 0)
                    self._selection_handles.translate(1, 0)
            elif _key == Qt.Key.Key_R:
                self.switch_mode(Mode.ROI_RECTANGLE)
            elif _key == Qt.Key.Key_E:
                self.switch_mode(Mode.ROI_ELLIPSE)
            elif _key == Qt.Key.Key_P:
                # switch similar modes in turn
                if self._mode is Mode.ROI_POINT:
                    self.switch_mode(Mode.ROI_POINTS)
                else:
                    self.switch_mode(Mode.ROI_POINT)
            elif _key == Qt.Key.Key_L:
                if self._mode is Mode.ROI_LINE:
                    self.switch_mode(Mode.ROI_SEGMENTED_LINE)
                else:
                    self.switch_mode(Mode.ROI_LINE)
            elif _key == Qt.Key.Key_G:
                self.switch_mode(Mode.ROI_POLYGON)
            elif _key == Qt.Key.Key_S:
                self.switch_mode(Mode.SELECT)
            elif _key == Qt.Key.Key_Z:
                self.switch_mode(Mode.PAN_ZOOM)
            elif _key == Qt.Key.Key_T:
                self.add_current_roi()
            elif _key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self.remove_current_item(remove_from_list=True)
            elif _key == Qt.Key.Key_V:
                self.toggle_roi_list_visibility()
        return super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent | None) -> None:
        if event is None:
            return super().keyReleaseEvent(event)
        if event.key() == Qt.Key.Key_Space:
            self.set_mode(self._last_mode_before_key_hold)
        return super().keyReleaseEvent(event)
