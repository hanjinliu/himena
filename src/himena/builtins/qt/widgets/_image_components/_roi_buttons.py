from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from superqt import QIconifyIcon
from ._graphics_view import Mode
from himena.qt._utils import qsignal_blocker


def _tool_btn(icon_name: str, tooltip: str) -> QtW.QToolButton:
    btn = QtW.QToolButton()
    btn.setIcon(QIconifyIcon(icon_name))
    btn.setCheckable(True)
    btn.setToolTip(tooltip)
    return btn


class QRoiButtons(QtW.QWidget):
    mode_changed = QtCore.Signal(Mode)

    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self._btn_panzoom = _tool_btn(
            icon_name="mdi:magnify-expand",
            tooltip="Pan/zoom mode",
        )
        self._btn_select = _tool_btn(
            icon_name="mdi:cursor-default",
            tooltip="Select mode",
        )
        self._btn_rect = _tool_btn(
            icon_name="mdi:vector-rectangle",
            tooltip="Add rectangles",
        )
        self._btn_ellipse = _tool_btn(
            icon_name="mdi:vector-ellipse",
            tooltip="Add ellipses",
        )
        self._btn_line = _tool_btn(
            icon_name="mdi:vector-line",
            tooltip="Add lines",
        )
        self._btn_segmented_line = _tool_btn(
            icon_name="mdi:vector-polyline",
            tooltip="Add segmented lines",
        )
        self._btn_polygon = _tool_btn(
            icon_name="mdi:vector-polygon",
            tooltip="Add polygons",
        )
        self._btn_point = _tool_btn(
            icon_name="mdi:vector-point",
            tooltip="Add points",
        )
        self._btn_points = _tool_btn(
            icon_name="mdi:vector-point-plus",
            tooltip="Add multiple points",
        )
        self._button_group = QtW.QButtonGroup()
        self._button_group.addButton(self._btn_panzoom)
        self._button_group.addButton(self._btn_select)
        self._button_group.addButton(self._btn_rect)
        self._button_group.addButton(self._btn_ellipse)
        self._button_group.addButton(self._btn_line)
        self._button_group.addButton(self._btn_segmented_line)
        self._button_group.addButton(self._btn_polygon)
        self._button_group.addButton(self._btn_point)
        self._button_group.addButton(self._btn_points)
        self._button_group.setExclusive(True)
        self._button_group.buttonReleased.connect(self.btn_released)

        layout.addWidget(self._btn_panzoom)
        layout.addWidget(self._btn_select)
        layout.addWidget(self._btn_rect)
        layout.addWidget(self._btn_ellipse)
        layout.addWidget(self._btn_line)
        layout.addWidget(self._btn_segmented_line)
        layout.addWidget(self._btn_polygon)
        layout.addWidget(self._btn_point)
        layout.addWidget(self._btn_points)

        self._btn_map = {
            Mode.PAN_ZOOM: self._btn_panzoom,
            Mode.SELECT: self._btn_select,
            Mode.ROI_RECTANGLE: self._btn_rect,
            Mode.ROI_ELLIPSE: self._btn_ellipse,
            Mode.ROI_LINE: self._btn_line,
            Mode.ROI_SEGMENTED_LINE: self._btn_segmented_line,
            Mode.ROI_POLYGON: self._btn_polygon,
            Mode.ROI_POINT: self._btn_point,
            Mode.ROI_POINTS: self._btn_points,
        }
        self._btn_map_inv = {v: k for k, v in self._btn_map.items()}
        self.setFixedHeight(22)
        self._btn_panzoom.setChecked(True)

    def set_mode(self, mode: Mode):
        btn = self._btn_map[mode]
        with qsignal_blocker(self._button_group):
            btn.setChecked(True)

    def btn_released(self, btn: QtW.QToolButton):
        mode = self._btn_map_inv[btn]
        self.mode_changed.emit(mode)
