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
    btn.setFixedSize(22, 22)
    return btn


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
            icon_name="mdi:magnify-expand",
            tooltip="Pan/zoom mode (Z, Space)",
        )
        self._btn_select = _tool_btn(
            icon_name="mdi:cursor-default",
            tooltip="Select mode (S)",
        )
        self._btn_rect = _tool_btn(
            icon_name="mdi:vector-rectangle",
            tooltip="Add rectangles (R)",
        )
        self._btn_ellipse = _tool_btn(
            icon_name="mdi:vector-ellipse",
            tooltip="Add ellipses (E)",
        )
        self._btn_line = _tool_btn(
            icon_name="mdi:vector-line",
            tooltip="Add lines (L)",
        )
        self._btn_segmented_line = _tool_btn(
            icon_name="mdi:vector-polyline",
            tooltip="Add segmented lines (L x 2)",
        )
        self._btn_polygon = _tool_btn(
            icon_name="mdi:vector-polygon",
            tooltip="Add polygons (G)",
        )
        self._btn_point = _tool_btn(
            icon_name="mdi:vector-point",
            tooltip="Add points (P)",
        )
        self._btn_points = _tool_btn(
            icon_name="mdi:vector-point-plus",
            tooltip="Add multiple points (P x 2)",
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

        layout.addWidget(self._btn_panzoom, 0, 0)
        layout.addWidget(self._btn_select, 0, 1)
        layout.addWidget(self._btn_rect, 0, 2)
        layout.addWidget(self._btn_ellipse, 1, 0)
        layout.addWidget(self._btn_line, 1, 1)
        layout.addWidget(self._btn_segmented_line, 1, 2)
        layout.addWidget(self._btn_polygon, 2, 0)
        layout.addWidget(self._btn_point, 2, 1)
        layout.addWidget(self._btn_points, 2, 2)

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
        self.setFixedHeight(70)
        self._btn_panzoom.setChecked(True)

    def set_mode(self, mode: Mode):
        btn = self._btn_map[mode]
        with qsignal_blocker(self._button_group):
            btn.setChecked(True)

    def btn_released(self, btn: QtW.QToolButton):
        mode = self._btn_map_inv[btn]
        self.mode_changed.emit(mode)
