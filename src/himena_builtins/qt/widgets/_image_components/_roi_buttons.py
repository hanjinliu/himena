from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt import QIconifyIcon

from himena.widgets import set_status_tip
from himena_builtins.qt.widgets._image_components._graphics_view import MouseMode
from himena_builtins.qt.widgets._image_components import _roi_items
from himena.qt._utils import qsignal_blocker

if TYPE_CHECKING:
    from himena_builtins.qt.widgets.image import QImageView


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

_THUMBNAIL_ROIS: dict[MouseMode, _roi_items.QRoi] = {
    MouseMode.ROI_RECTANGLE: _roi_items.QRectangleRoi(0, 0, 10, 8),
    MouseMode.ROI_ROTATED_RECTANGLE: _roi_items.QRotatedRectangleRoi(
        QtCore.QPointF(0, -2), QtCore.QPointF(4, 2), 3.6
    ),
    MouseMode.ROI_ELLIPSE: _roi_items.QEllipseRoi(0, 0, 10, 8),
    MouseMode.ROI_ROTATED_ELLIPSE: _roi_items.QRotatedEllipseRoi(
        QtCore.QPointF(0, -2), QtCore.QPointF(4, 2), 3.6
    ),
    MouseMode.ROI_LINE: _roi_items.QLineRoi(0, 0, 10, 8),
    MouseMode.ROI_SEGMENTED_LINE: _roi_items.QSegmentedLineRoi(
        [0, 4, 8, 12], [10, 4, 6, 0]
    ),
    MouseMode.ROI_POLYGON: _roi_items.QPolygonRoi(
        [0, -5, -3, 3, 5, 0], [-2, -5, 3, 3, -5, -2]
    ),
    MouseMode.ROI_POINT: _roi_items.QPointRoi(0, 0),
    MouseMode.ROI_POINTS: _roi_items.QPointsRoi([], []),
}


class QRoiButtons(QtW.QWidget):
    def __init__(self, view: QImageView):
        super().__init__()
        self._img_view = view._img_view
        layout = QtW.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._btn_map: dict[MouseMode, QtW.QToolButton] = {
            MouseMode.PAN_ZOOM: _tool_btn(
                icon_name=ICON_ZOOM,
                tooltip="Pan/zoom mode (Z, Space)",
            ),
            MouseMode.SELECT: _tool_btn(
                icon_name=ICON_SELECT,
                tooltip="Select mode (S)",
            ),
            MouseMode.ROI_RECTANGLE: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_RECTANGLE],
                tooltip="Add rectangles (R)",
            ),
            MouseMode.ROI_ROTATED_RECTANGLE: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_ROTATED_RECTANGLE],
                tooltip="Add rotated rectangles (Shift+R)",
            ),
            MouseMode.ROI_ELLIPSE: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_ELLIPSE],
                tooltip="Add ellipses (E)",
            ),
            MouseMode.ROI_ROTATED_ELLIPSE: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_ROTATED_ELLIPSE],
                tooltip="Add rotated ellipses (Shift+E)",
            ),
            MouseMode.ROI_LINE: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_LINE],
                tooltip="Add lines (L)",
            ),
            MouseMode.ROI_SEGMENTED_LINE: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_SEGMENTED_LINE],
                tooltip="Add segmented lines (Shift+L)",
            ),
            MouseMode.ROI_POLYGON: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_POLYGON],
                tooltip="Add polygons (G)",
            ),
            MouseMode.ROI_POINT: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_POINT],
                tooltip="Add points (P)",
            ),
            MouseMode.ROI_POINTS: QRoiToolButton(
                _THUMBNAIL_ROIS[MouseMode.ROI_POINTS],
                tooltip="Add multiple points (Shift+P)",
            ),
        }
        self._btn_map_inv = {v: k for k, v in self._btn_map.items()}
        self._button_group = QtW.QButtonGroup()
        for btn in self._btn_map.values():
            self._button_group.addButton(btn)
        self._button_group.setExclusive(True)
        self._button_group.buttonReleased.connect(self.btn_released)

        layout.addWidget(self._btn_map[MouseMode.PAN_ZOOM], 0, 0)
        layout.addWidget(self._btn_map[MouseMode.SELECT], 0, 1)
        layout.addWidget(self._btn_map[MouseMode.ROI_RECTANGLE], 1, 0)
        layout.addWidget(self._btn_map[MouseMode.ROI_ROTATED_RECTANGLE], 1, 1)
        layout.addWidget(self._btn_map[MouseMode.ROI_ELLIPSE], 1, 2)
        layout.addWidget(self._btn_map[MouseMode.ROI_ROTATED_ELLIPSE], 1, 3)
        layout.addWidget(self._btn_map[MouseMode.ROI_LINE], 2, 0)
        layout.addWidget(self._btn_map[MouseMode.ROI_SEGMENTED_LINE], 2, 1)
        layout.addWidget(self._btn_map[MouseMode.ROI_POLYGON], 2, 2)
        layout.addWidget(self._btn_map[MouseMode.ROI_POINT], 3, 0)
        layout.addWidget(self._btn_map[MouseMode.ROI_POINTS], 3, 1)

        self.setFixedHeight(70)
        self._btn_map[MouseMode.PAN_ZOOM].setChecked(True)
        self._img_view.mode_changed.connect(self.set_mode)

    def set_mode(self, mode: MouseMode):
        if btn := self._btn_map.get(mode):
            with qsignal_blocker(self._button_group):
                btn.setChecked(True)
        else:
            with qsignal_blocker(self._button_group):
                for button in self._button_group.buttons():
                    button.setChecked(False)

    def btn_released(self, btn: QtW.QToolButton):
        mode = self._btn_map_inv[btn]
        self._img_view.switch_mode(mode)
        mode_name = mode.name.replace("_", " ")
        if mode_name.startswith("ROI "):
            mode_name = mode_name[4:]
        set_status_tip(f"Switched to {mode_name} mode.")

    def _update_colors(self, color: QtGui.QColor):
        for mode, btn in self._btn_map.items():
            if roi := _THUMBNAIL_ROIS.get(mode):
                btn.setIcon(_roi_tool_btn_icon(roi, color))
        self._btn_map[MouseMode.PAN_ZOOM].setIcon(
            _tool_btn_icon(ICON_ZOOM, color=color.name())
        )
        self._btn_map[MouseMode.SELECT].setIcon(
            _tool_btn_icon(ICON_SELECT, color=color.name())
        )
