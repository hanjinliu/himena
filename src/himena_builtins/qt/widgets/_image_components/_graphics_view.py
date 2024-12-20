from __future__ import annotations

import logging
from enum import Enum, auto
import math
from typing import Iterable
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
    QRotatedRectangleRoi,
    QSegmentedLineRoi,
)
from ._handles import QHandleRect, RoiSelectionHandles
from ._scale_bar import QScaleBarItem
from himena.qt._utils import ndarray_to_qimage
from himena.widgets import set_status_tip

_LOGGER = logging.getLogger(__name__)


class Mode(Enum):
    """Mouse interaction modes for the image graphics view."""

    SELECT = auto()
    PAN_ZOOM = auto()
    ROI_RECTANGLE = auto()
    ROI_ROTATED_RECTANGLE = auto()
    ROI_ELLIPSE = auto()
    ROI_POINT = auto()
    ROI_POINTS = auto()
    ROI_POLYGON = auto()
    ROI_SEGMENTED_LINE = auto()
    ROI_LINE = auto()


SIMPLE_ROI_MODES = frozenset({
    Mode.ROI_RECTANGLE, Mode.ROI_ROTATED_RECTANGLE, Mode.ROI_ELLIPSE, Mode.ROI_POINT,
    Mode.ROI_LINE
})  # fmt: skip
MULTIPOINT_ROI_MODES = frozenset({
    Mode.ROI_POINTS, Mode.ROI_POLYGON, Mode.ROI_SEGMENTED_LINE
})  # fmt: skip
ROI_MODES = SIMPLE_ROI_MODES | MULTIPOINT_ROI_MODES
MULTIPOINT_ROI_CLASSES = (QPolygonRoi, QSegmentedLineRoi, QPointsRoi)


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

    def paint(self, painter, option, widget=None):
        if self._qimage.isNull():
            return

        painter.setCompositionMode(self._comp_mode)
        painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform, self._smoothing
        )
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
            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0)))
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
    mode_changed = QtCore.Signal(Mode)
    hovered = QtCore.Signal(QtCore.QPointF)
    geometry_changed = QtCore.Signal(QtCore.QRectF)

    Mode = Mode

    def __init__(self, roi_visible: bool = False, roi_pen: QtGui.QPen | None = None):
        ### Attributes ###
        self._pos_drag_start: QtCore.QPoint | None = None
        self._pos_drag_prev: QtCore.QPoint | None = None
        self._is_key_hold = False
        self._roi_items: list[QRoi] = []
        self._current_roi_item: QRoi | None = None
        self._is_current_roi_item_not_registered = False
        self._roi_pen = roi_pen or QtGui.QPen(QtGui.QColor(225, 225, 0), 3)
        self._roi_pen.setCosmetic(True)
        self._mode = Mode.PAN_ZOOM
        self._last_mode_before_key_hold = Mode.PAN_ZOOM
        self._is_drawing_multipoints = False
        self._is_rois_visible = roi_visible
        self._selection_handles = RoiSelectionHandles(self)
        self._initialized = False
        self._image_widgets: list[QImageGraphicsWidget] = []
        super().__init__()
        self.switch_mode(Mode.PAN_ZOOM)
        self._qroi_labels = self.addItem(QRoiLabels(self))
        self._qroi_labels.setZValue(10000)
        self._scale_bar_widget = self.addItem(QScaleBarItem(self))
        self._scale_bar_widget.setZValue(10000)
        self._scale_bar_widget.setVisible(False)
        self.geometry_changed.connect(self._scale_bar_widget.update_rect)
        self._internal_clipboard: QRoi | None = None

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
        widget = self._image_widgets[idx]
        if img is None:
            widget.setVisible(False)
        else:
            widget.set_image(img)
            widget.setVisible(True)
        self._qroi_labels.set_bounding_rect(self._image_widgets[0].boundingRect())
        self._scale_bar_widget.set_bounding_rect(self._image_widgets[0].boundingRect())

    def set_image_blending(self, opaque: list[bool]):
        is_first = True
        for img, is_opaque in zip(self._image_widgets, opaque):
            if is_opaque and is_first:
                is_first = False
                img.set_additive(False)
            else:
                img.set_additive(True)

    def clear_rois(self):
        scene = self.scene()
        for item in self._roi_items:
            scene.removeItem(item)
        self._roi_items.clear()
        if not self._is_current_roi_item_not_registered:
            self.remove_current_item()

    def extend_qrois(self, rois: Iterable[QRoi]):
        """Set Qt ROIs to display."""
        for roi in rois:
            self.scene().addItem(roi)
            roi.setVisible(self._is_rois_visible)
            self._roi_items.append(roi)

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
        for im in self._image_widgets:
            im.setSmoothingEnabled(enabled)

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()

    def resizeEvent(self, event: QtGui.QResizeEvent):
        # Dynamically resize the image to keep the current zoom factor
        old_size = event.oldSize()
        new_size = event.size()
        if (w_new := new_size.width()) < 10 or (h_new := new_size.height()) < 10:
            return super().resizeEvent(event)
        if (w_old := old_size.width()) == 0 or (h_old := old_size.height()) == 0:
            ratio = 1.0
        else:
            ratio = math.sqrt(w_new / w_old * h_new / h_old)

        self.scale_and_update_handles(ratio)
        self._inform_scale()
        if not self._initialized:
            self.initialize()
        return super().resizeEvent(event)

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

    def wheelEvent(self, event):
        # Zoom in/out using the mouse wheel
        factor = 1.1

        if event.angleDelta().y() > 0:
            zoom_factor = factor
        else:
            zoom_factor = 1 / factor
        super().wheelEvent(event)
        # NOTE: for some reason, following lines must be called after super().wheelEvent
        self.scale_and_update_handles(zoom_factor)
        self._inform_scale()
        return None

    def scale_and_update_handles(self, factor: float):
        """Scale the view and update the selection handle sizes."""
        if factor > 0:
            self.scale(factor, factor)
        tr = self.transform()
        self._selection_handles.update_handle_size(tr.m11())
        self.geometry_changed.emit(self.sceneRect())

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
        elif isinstance(item, QPointRoi):
            self._selection_handles.connect_point(item)
        elif isinstance(item, QRotatedRectangleRoi):
            self._selection_handles.connect_rotated_rect(item)
        if isinstance(item, QRoi):
            self._current_roi_item = item
            item.setVisible(True)
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
        if event.button() == Qt.MouseButton.RightButton:
            return super().mousePressEvent(event)
        if self._mode in ROI_MODES:
            grabbing = self.scene().grabSource()
            if grabbing is not None and grabbing is not self:
                return super().mousePressEvent(event)
            self.scene().setGrabSource(self)
            if self.mode() in MULTIPOINT_ROI_MODES:
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
            if self.mode() is Mode.ROI_LINE:
                self.set_current_roi(
                    QLineRoi(p.x(), p.y(), p.x(), p.y()).withPen(self._roi_pen)
                )
                self._selection_handles.connect_line(self._current_roi_item)
            elif self.mode() is Mode.ROI_RECTANGLE:
                self.set_current_roi(
                    QRectangleRoi(p.x(), p.y(), 0, 0).withPen(self._roi_pen)
                )
                self._selection_handles.connect_rect(self._current_roi_item)
            elif self.mode() is Mode.ROI_ELLIPSE:
                self.set_current_roi(
                    QEllipseRoi(p.x(), p.y(), 0, 0).withPen(self._roi_pen)
                )
                self._selection_handles.connect_rect(self._current_roi_item)
            elif self.mode() is Mode.ROI_ROTATED_RECTANGLE:
                self.set_current_roi(QRotatedRectangleRoi(p, p).withPen(self._roi_pen))
                self._selection_handles.connect_rotated_rect(self._current_roi_item)
            elif self.mode() is Mode.ROI_POINT:
                pass

        elif self.mode() is Mode.SELECT:
            self.select_item_at(self.mapToScene(event.pos()))
            self.scene().setGrabSource(self)
        elif self.mode() is Mode.PAN_ZOOM:
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            self.scene().setGrabSource(self)

        return super().mousePressEvent(event)

    def _mouse_move_pan_zoom(self, event: QtGui.QMouseEvent):
        delta = event.pos() - self._pos_drag_prev
        self.move_items_by(delta.x(), delta.y())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        # Move the image using the mouse
        pos = self.mapToScene(event.pos())
        _shift_down = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
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
            if self.mode() is Mode.PAN_ZOOM:
                self._mouse_move_pan_zoom(event)
            elif self.mode() is Mode.ROI_LINE:
                if isinstance(item := self._current_roi_item, QLineRoi):
                    if _shift_down:
                        pos = _find_nice_position(pos0, pos)
                    item.setLine(pos0.x(), pos0.y(), pos.x(), pos.y())
            elif self.mode() in (Mode.ROI_RECTANGLE, Mode.ROI_ELLIPSE):
                if isinstance(self._current_roi_item, (QRectangleRoi, QEllipseRoi)):
                    x0, x1 = pos.x(), pos0.x()
                    y0, y1 = pos.y(), pos0.y()
                    width = abs(x1 - x0)
                    height = abs(y1 - y0)
                    if _shift_down:
                        width = height = min(width, height)
                    self._current_roi_item.setRect(
                        min(x0, x1), min(y0, y1), width, height
                    )
            elif self.mode() is Mode.ROI_ROTATED_RECTANGLE:
                if isinstance(self._current_roi_item, QRotatedRectangleRoi):
                    if _shift_down:
                        pos = _find_nice_position(pos0, pos)
                    self._current_roi_item.set_end(pos)
            elif self.mode() is Mode.SELECT:
                if item := self._current_roi_item:
                    delta = pos - self.mapToScene(self._pos_drag_prev)
                    item.translate(delta.x(), delta.y())
                else:
                    # just forward to the pan-zoom mode
                    self._mouse_move_pan_zoom(event)
            elif self.mode() in (Mode.ROI_POINTS, Mode.ROI_POINT):
                self._mouse_move_pan_zoom(event)

            self._pos_drag_prev = event.pos()
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if (
            self._pos_drag_start == event.pos()
            and event.button() == Qt.MouseButton.LeftButton
        ):  # left click
            p0 = self.mapToScene(self._pos_drag_start)
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
            elif self.mode() in (
                Mode.ROI_LINE,
                Mode.ROI_RECTANGLE,
                Mode.ROI_ELLIPSE,
                Mode.ROI_ROTATED_RECTANGLE,
            ):
                self.remove_current_item()
        elif (
            self._pos_drag_start == event.pos()
            and event.button() == Qt.MouseButton.RightButton
        ):  # right click
            return super().mouseReleaseEvent(event)
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
        if item := self._current_roi_item:
            self._is_current_roi_item_not_registered = False
            if len(self._roi_items) > 0 and self._roi_items[-1] is item:
                # do not add the same item
                return
            _LOGGER.info(f"Added ROI item {item}")
            self._roi_items.append(item)
            self._qroi_labels.update()
            self.roi_added.emit(item)

    def keyPressEvent(self, event: QtGui.QKeyEvent | None) -> None:
        if event is None:
            return None
        _mods = event.modifiers()
        _key = event.key()
        if _mods == Qt.KeyboardModifier.NoModifier:
            if _key == Qt.Key.Key_Space:
                if not self._is_key_hold:
                    self._last_mode_before_key_hold = self.mode()
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
                if self.mode() is Mode.ROI_RECTANGLE:
                    self.switch_mode(Mode.ROI_ROTATED_RECTANGLE)
                else:
                    self.switch_mode(Mode.ROI_RECTANGLE)
            elif _key == Qt.Key.Key_E:
                self.switch_mode(Mode.ROI_ELLIPSE)
            elif _key == Qt.Key.Key_P:
                # switch similar modes in turn
                if self.mode() is Mode.ROI_POINT:
                    self.switch_mode(Mode.ROI_POINTS)
                else:
                    self.switch_mode(Mode.ROI_POINT)
            elif _key == Qt.Key.Key_L:
                if self.mode() is Mode.ROI_LINE:
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
                if not self._is_key_hold:
                    self.remove_current_item(remove_from_list=True)
            elif _key == Qt.Key.Key_V:
                if not self._is_key_hold:
                    self.set_show_rois(not self._is_rois_visible)
        elif _mods == Qt.KeyboardModifier.ControlModifier:
            if _key == Qt.Key.Key_A:
                ny, nx = self._image_widgets[0]._img.shape[:2]
                self.set_current_roi(QRectangleRoi(0, 0, nx, ny).withPen(self._roi_pen))
                self._selection_handles.connect_rect(self._current_roi_item)
            elif _key == Qt.Key.Key_X:
                if self._current_roi_item is not None:
                    self._internal_clipboard = self._current_roi_item.copy()
                    self.remove_current_item(remove_from_list=True)
            elif _key == Qt.Key.Key_C:
                if self._current_roi_item is not None:
                    self._internal_clipboard = self._current_roi_item.copy()
            elif _key == Qt.Key.Key_V and self._internal_clipboard:
                self._paste_roi()
            elif _key == Qt.Key.Key_D:  # duplicate ROI
                if self._current_roi_item is not None:
                    self._internal_clipboard = self._current_roi_item.copy()
                    self._paste_roi()
        self._is_key_hold = True
        return None

    def keyReleaseEvent(self, event: QtGui.QKeyEvent | None) -> None:
        self._is_key_hold = False
        if event is None:
            return None
        if event.key() == Qt.Key.Key_Space:
            self.set_mode(self._last_mode_before_key_hold)
        return None

    def _paste_roi(self):
        item = self._internal_clipboard
        if self._current_roi_item and self._is_current_roi_item_not_registered:
            self.add_current_roi()
        else:
            self.remove_current_item()
        sx, sy = self.transform().m11(), self.transform().m22()
        item.translate(4 / sx, 4 / sy)
        item_copy = item.copy()
        self.set_current_roi(item_copy)
        self._selection_handles.connect_rect(item_copy)
        self._internal_clipboard = item_copy  # needed for Ctrl+V x2
        self._is_current_roi_item_not_registered = True


def _find_nice_position(pos0: QtCore.QPointF, pos1: QtCore.QPointF) -> QtCore.QPointF:
    """Find the "nice" position when Shift is pressed."""
    x0, y0 = pos0.x(), pos0.y()
    x1, y1 = pos1.x(), pos1.y()
    ang = math.atan2(y1 - y0, x1 - x0)
    pi = math.pi
    if -pi / 8 < ang <= pi / 8:  # right direction
        y1 = y0
    elif 3 * pi / 8 < ang <= 5 * pi / 8:  # down direction
        x1 = x0
    elif -5 * pi / 8 < ang <= -3 * pi / 8:  # up direction
        x1 = x0
    elif ang <= -7 * pi / 8 or 7 * pi / 8 < ang:  # left direction
        y1 = y0
    elif pi / 8 < ang <= 3 * pi / 8:  # down-right direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 + abs(y1 - y0)
        else:
            y1 = y0 + abs(x1 - x0)
    elif -3 * pi / 8 < ang <= -pi / 8:  # up-left direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 + abs(y1 - y0)
        else:
            y1 = y0 - abs(x1 - x0)
    elif 5 * pi / 8 < ang <= 7 * pi / 8:  # down-left direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 - abs(y1 - y0)
        else:
            y1 = y0 + abs(x1 - x0)
    elif -7 * pi / 8 < ang <= -5 * pi / 8:  # up-right direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 - abs(y1 - y0)
        else:
            y1 = y0 - abs(x1 - x0)
    return QtCore.QPointF(x1, y1)
