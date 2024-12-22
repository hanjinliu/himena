from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt import QIconifyIcon
from ._graphics_view import Mode
from . import _roi_items
from himena.qt._utils import qsignal_blocker


def _tool_btn(
    icon_name: str,
    tooltip: str,
    color: QtGui.QColor = QtGui.QColor(0, 0, 0),
) -> QtW.QToolButton:
    btn = QtW.QToolButton()
    btn.setIcon(_tool_btn_icon(icon_name, color=color.name()))
    btn.setCheckable(True)
    btn.setToolTip(tooltip)
    btn.setFixedSize(22, 22)
    return btn


class QRoiToolButton(QtW.QToolButton):
    def __init__(
        self,
        roi: _roi_items.QRoi,
        tooltip: str,
        color: QtGui.QColor = QtGui.QColor(0, 0, 0),
    ):
        super().__init__()
        self._roi = roi
        self.setIcon(_roi_tool_btn_icon(roi, color=color))
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setFixedSize(22, 22)


def _roi_tool_btn_icon(roi: _roi_items.QRoi, color: QtGui.QColor):
    pixmap = QtGui.QPixmap(20, 20)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    pen = QtGui.QPen(color, 2)
    pen.setCosmetic(True)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
    icon = QtGui.QIcon(roi.withPen(pen).makeThumbnail(pixmap))
    return icon


def _tool_btn_icon(icon_name: str, color: str) -> QtGui.QIcon:
    return QIconifyIcon(icon_name, color=color)


ICON_ZOOM = "mdi:magnify-expand"
ICON_SELECT = "mdi:cursor-default"

_THUMBNAIL_ROIS: dict[Mode, _roi_items.QRoi] = {
    Mode.ROI_RECTANGLE: _roi_items.QRectangleRoi(0, 0, 10, 8),
    Mode.ROI_ROTATED_RECTANGLE: _roi_items.QRotatedRectangleRoi(
        QtCore.QPointF(0, -2), QtCore.QPointF(4, 2), 3.6
    ),
    Mode.ROI_ELLIPSE: _roi_items.QEllipseRoi(0, 0, 10, 8),
    Mode.ROI_LINE: _roi_items.QLineRoi(0, 0, 10, 8),
    Mode.ROI_SEGMENTED_LINE: _roi_items.QSegmentedLineRoi([0, 4, 8, 12], [10, 4, 6, 0]),
    Mode.ROI_POLYGON: _roi_items.QPolygonRoi(
        [0, -5, -3, 3, 5, 0], [-2, -5, 3, 3, -5, -2]
    ),
    Mode.ROI_POINT: _roi_items.QPointRoi(0, 0),
    Mode.ROI_POINTS: _roi_items.QPointsRoi([], []),
}


class QRoiButtons(QtW.QWidget):
    mode_changed = QtCore.Signal(Mode)

    def __init__(self):
        super().__init__()
        layout = QtW.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._btn_panzoom = _tool_btn(
            icon_name=ICON_ZOOM,
            tooltip="Pan/zoom mode (Z, Space)",
        )
        self._btn_select = _tool_btn(
            icon_name=ICON_SELECT,
            tooltip="Select mode (S)",
        )
        self._btn_rect = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_RECTANGLE],
            tooltip="Add rectangles (R)",
        )
        self._btn_rot_rect = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_ROTATED_RECTANGLE],
            tooltip="Add rotated rectangles (R x 2)",
        )
        self._btn_ellipse = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_ELLIPSE],
            tooltip="Add ellipses (E)",
        )
        self._btn_line = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_LINE],
            tooltip="Add lines (L)",
        )
        self._btn_segmented_line = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_SEGMENTED_LINE],
            tooltip="Add segmented lines (L x 2)",
        )
        self._btn_polygon = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_POLYGON],
            tooltip="Add polygons (G)",
        )
        self._btn_point = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_POINT],
            tooltip="Add points (P)",
        )
        self._btn_points = QRoiToolButton(
            _THUMBNAIL_ROIS[Mode.ROI_POINTS],
            tooltip="Add multiple points (P x 2)",
        )
        self._button_group = QtW.QButtonGroup()
        self._button_group.addButton(self._btn_panzoom)
        self._button_group.addButton(self._btn_select)
        self._button_group.addButton(self._btn_rect)
        self._button_group.addButton(self._btn_rot_rect)
        self._button_group.addButton(self._btn_ellipse)
        self._button_group.addButton(self._btn_line)
        self._button_group.addButton(self._btn_segmented_line)
        self._button_group.addButton(self._btn_polygon)
        self._button_group.addButton(self._btn_point)
        self._button_group.addButton(self._btn_points)
        self._button_group.setExclusive(True)
        self._button_group.buttonReleased.connect(self.btn_released)

        layout.addWidget(self._btn_panzoom, 0, 0)
        layout.addWidget(self._btn_select, 0, 1)
        layout.addWidget(self._btn_rect, 1, 0)
        layout.addWidget(self._btn_rot_rect, 1, 1)
        layout.addWidget(self._btn_ellipse, 1, 2)
        layout.addWidget(self._btn_line, 1, 3)
        layout.addWidget(self._btn_segmented_line, 2, 0)
        layout.addWidget(self._btn_polygon, 2, 1)
        layout.addWidget(self._btn_point, 2, 2)
        layout.addWidget(self._btn_points, 2, 3)

        self._btn_map = {
            Mode.PAN_ZOOM: self._btn_panzoom,
            Mode.SELECT: self._btn_select,
            Mode.ROI_RECTANGLE: self._btn_rect,
            Mode.ROI_ROTATED_RECTANGLE: self._btn_rot_rect,
            Mode.ROI_ELLIPSE: self._btn_ellipse,
            Mode.ROI_LINE: self._btn_line,
            Mode.ROI_SEGMENTED_LINE: self._btn_segmented_line,
            Mode.ROI_POLYGON: self._btn_polygon,
            Mode.ROI_POINT: self._btn_point,
            Mode.ROI_POINTS: self._btn_points,
        }
        self._btn_map_inv = {v: k for k, v in self._btn_map.items()}
        self.setFixedHeight(70)
        self._btn_panzoom.setChecked(True)

    def set_mode(self, mode: Mode):
        if btn := self._btn_map.get(mode):
            with qsignal_blocker(self._button_group):
                btn.setChecked(True)

    def btn_released(self, btn: QtW.QToolButton):
        mode = self._btn_map_inv[btn]
        self.mode_changed.emit(mode)

    def _update_colors(self, color: QtGui.QColor):
        for mode, btn in self._btn_map.items():
            if roi := _THUMBNAIL_ROIS.get(mode):
                btn.setIcon(_roi_tool_btn_icon(roi, color))
        self._btn_panzoom.setIcon(_tool_btn_icon(ICON_ZOOM, color=color.name()))
        self._btn_select.setIcon(_tool_btn_icon(ICON_SELECT, color=color.name()))
