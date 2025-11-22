from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from superqt import QLabeledDoubleSlider, QToggleSwitch, QElidingLabel
from superqt.utils import qthrottled

from himena.consts import DefaultFontFamily
from himena.qt import qsignal_blocker, ndarray_to_qimage, QColoredToolButton
from himena_builtins._consts import ICON_PATH
from himena_builtins.qt.widgets._image_components import QHistogramView
from himena.utils.enum import StrEnum

if TYPE_CHECKING:
    from himena_builtins.qt.widgets.image import QImageViewBase, ChannelInfo


class ImageType(StrEnum):
    SINGLE = "Single"
    RGB = "RGB"
    MULTI = "Multi"
    OTHERS = "Others"


class ComplexMode(StrEnum):
    REAL = "Real"
    IMAG = "Imag"
    ABS = "Abs"
    LOG_ABS = "Log Abs"
    PHASE = "Phase"


class ChannelMode(StrEnum):
    COMP = "Comp."
    MONO = "Mono"
    GRAY = "Gray"


class RGBMode(StrEnum):
    COLOR = "Color"
    GRAY = "Gray"


class QImageViewControlBase(QtW.QWidget):
    def __init__(self, image_view: QImageViewBase):
        super().__init__()
        self._image_view = image_view
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._interp_check_box = QInterpolationSwitch(self)
        self._interp_check_box.toggled.connect(self._interpolation_changed)

        self._hover_info = QElidingLabel()
        self._hover_info.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._hover_info.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        for wdt in self._widgets_to_add():
            layout.addWidget(wdt)

    def _widgets_to_add(self) -> list[QtW.QWidget]:
        return [self._hover_info, self._interp_check_box]

    def _interpolation_changed(self, checked: bool):
        self._image_view._img_view.setSmoothing(checked)

    def update_rgb_channel_dtype(self, is_rgb: bool, nchannels: int, dtype):
        pass


class QImageViewControl(QImageViewControlBase):
    def __init__(self, image_view: QImageViewBase):
        self._complex_mode_old = "Abs"
        self._cmp_mode_combo = QtW.QComboBox()
        self._cmp_mode_combo.addItems(
            [ComplexMode.REAL, ComplexMode.IMAG, ComplexMode.ABS, ComplexMode.LOG_ABS,
             ComplexMode.PHASE]
        )  # fmt: skip
        self._cmp_mode_combo.setCurrentIndex(2)
        self._cmp_mode_combo.setToolTip("Method to display complex data")

        self._chn_vis = QChannelToggleSwitches()

        self._chn_mode_combo = QtW.QComboBox()
        self._chn_mode_combo.addItems([""])
        self._chn_mode_combo.setToolTip("Method to display multi-channel data")
        self._image_type = ImageType.OTHERS

        self._auto_cont_btn = QColoredToolButton(
            self._auto_contrast, ICON_PATH / "auto_contrast_once.svg"
        )
        self._auto_cont_btn.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._auto_cont_btn.customContextMenuRequested.connect(
            self._exec_autocontrast_menu
        )
        self._auto_cont_live = False

        self._histogram = QHistogramView()
        self._histogram.setFixedWidth(120)
        super().__init__(image_view)
        self._cmp_mode_combo.hide()
        self._chn_mode_combo.hide()
        self._cmp_mode_combo.currentTextChanged.connect(self._on_complex_mode_change)
        self._chn_vis.stateChanged.connect(self._on_channel_visibility_change)
        self._histogram.clim_changed.connect(self._clim_changed)
        self._chn_mode_combo.currentTextChanged.connect(self._on_channel_mode_change)

    def _widgets_to_add(self) -> list[QtW.QWidget]:
        return [
            self._hover_info, self._cmp_mode_combo, self._chn_vis,
            self._chn_mode_combo, self._auto_cont_btn, self._histogram,
            self._interp_check_box,
        ]  # fmt: skip

    def update_rgb_channel_dtype(self, is_rgb: bool, nchannels: int, dtype):
        dtype = np.dtype(dtype)
        if is_rgb:
            kind = ImageType.RGB
        elif nchannels > 1:
            kind = ImageType.MULTI
        else:
            kind = ImageType.SINGLE
        if kind != self._image_type:
            if kind is ImageType.RGB:
                self._chn_mode_combo.clear()
                self._chn_mode_combo.addItems([RGBMode.COLOR, RGBMode.GRAY])
                self._chn_mode_combo.show()
                self._chn_vis.hide()
            elif kind is ImageType.MULTI:
                self._chn_mode_combo.clear()
                self._chn_mode_combo.addItems(
                    [ChannelMode.COMP, ChannelMode.MONO, ChannelMode.GRAY]
                )
                self._chn_mode_combo.show()
                self._chn_vis.show()
            else:
                self._chn_mode_combo.clear()
                self._chn_mode_combo.addItems([""])
                self._chn_mode_combo.hide()
                self._chn_vis.hide()
            self._image_type = kind
            self._chn_mode_combo.setCurrentIndex(0)
        self._cmp_mode_combo.setVisible(dtype.kind == "c")
        if dtype.kind in "uib":
            self._histogram.setValueFormat(".0f")
        else:
            self._histogram.setValueFormat(".3g")
        return None

    def complex_transform(self, arr: np.ndarray) -> np.ndarray:
        """Transform complex array according to the current complex mode."""
        if self._cmp_mode_combo.currentText() == ComplexMode.REAL:
            return arr.real
        if self._cmp_mode_combo.currentText() == ComplexMode.IMAG:
            return arr.imag
        if self._cmp_mode_combo.currentText() == ComplexMode.ABS:
            return np.abs(arr)
        if self._cmp_mode_combo.currentText() == ComplexMode.LOG_ABS:
            return np.log(np.abs(arr) + 1e-6)
        if self._cmp_mode_combo.currentText() == ComplexMode.PHASE:
            return np.angle(arr)
        return arr

    @qthrottled(timeout=100)
    def _clim_changed(self, clim: tuple[float, float]):
        view = self._image_view
        ch = view.current_channel()
        ch.clim = clim
        idx = ch.channel_index or 0
        imtup = view._current_image_slices[idx]
        with qsignal_blocker(self._histogram):
            _grays = (RGBMode.GRAY, ChannelMode.GRAY)
            if imtup.visible:
                arr = ch.transform_image(
                    view._current_image_slices[idx].arr,
                    complex_transform=self.complex_transform,
                    is_rgb=view._is_rgb,
                    is_gray=self._chn_mode_combo.currentText() in _grays,
                )
            else:
                arr = None
            view._img_view.set_array(idx, arr)

    def _exec_autocontrast_menu(self, *_):
        menu = QAutoContrastMenu(self)
        return menu.exec(QtGui.QCursor.pos())

    def _on_channel_mode_change(self, mode: str):
        self._chn_vis.setVisible(mode == ChannelMode.COMP)
        self._on_channel_visibility_change()

    def _channel_visibility(self) -> list[bool]:
        caxis = self._image_view._channel_axis
        if caxis is None:
            return [True]  # No channels, always visible
        is_composite = self._chn_mode_combo.currentText() == ChannelMode.COMP
        if is_composite:
            visibilities = self._chn_vis.check_states()
        else:
            visibilities = [False] * len(self._chn_vis._toggle_switches)
            sl = self._image_view._dims_slider.value()
            ith_channel = sl[caxis]
            if len(visibilities) <= ith_channel:
                return [True] * len(sl)  # before initialization
            visibilities[ith_channel] = True
        return visibilities

    def _on_channel_visibility_change(self):
        visibilities = self._channel_visibility()
        self._image_view._update_image_visibility(visibilities)

    def _on_complex_mode_change(self):
        cur = self._cmp_mode_combo.currentText()
        self._image_view._reset_image()
        self._complex_mode_old = cur
        # TODO: auto contrast and update colormap

    def _auto_contrast(self):
        """Auto contrast (right click to change settings)."""
        range_min, range_max = self._histogram._view_range
        if self._auto_cont_live and not self._auto_cont_btn.isChecked():
            return
        min_new, max_new = float("inf"), -float("inf")
        for item in self._histogram._hist_items:
            min_new = min(item._edges[0], min_new)
            max_new = max(item._edges[-1], max_new)
        if np.isinf(min_new) or np.isinf(max_new):
            return

        view = self._image_view
        sl = view._dims_slider.value()
        img_slice = view._get_image_slice_for_channel(sl)
        if img_slice.dtype.kind == "c":
            img_slice = self.complex_transform(img_slice)
        ch = view.current_channel(sl)
        min_old, max_old = ch.clim
        ch.clim = (min_new, max_new)
        view._set_image_slice(img_slice, ch)
        self._histogram.set_clim((min_new, max_new))

        # ensure both end is visible
        changed = False
        if min_new < min_old:
            range_min = min_new
            changed = True
        if max_new > max_old:
            range_max = max_new
            changed = True
        if changed:
            self._histogram.set_view_range(range_min, range_max)


class QImageLabelViewControl(QImageViewControlBase):
    def __init__(self, image_view: QImageViewBase):
        self._opacity_slider = QLabeledDoubleSlider(QtCore.Qt.Orientation.Horizontal)
        self._opacity_slider.setValue(0.6)
        self._opacity_slider.setFixedWidth(120)
        self._opacity_slider.setRange(0.0, 1.0)
        self._opacity_slider.setToolTip("Opacity of the label colors")
        super().__init__(image_view)
        self._opacity_slider.valueChanged.connect(image_view._reset_image)

    def _widgets_to_add(self):
        return [self._hover_info, self._opacity_slider, self._interp_check_box]


class QInterpolationSwitch(QtW.QAbstractButton):
    """Button for the interpolation mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Toggle interpolation mode")

    def paintEvent(self, a0: QtGui.QPaintEvent | None) -> None:
        p = QtGui.QPainter(self)
        p.drawPixmap(0, 0, self._make_pixmap(self.isChecked()))
        p.end()

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.sizeHint()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(20, 20)

    def _make_pixmap(self, state: bool) -> QtGui.QPixmap:
        img = np.array(
            [[1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1]],
            dtype=np.uint8,
        )
        img = img * 188 + 34
        qimg = ndarray_to_qimage(img)
        qpixmap = QtGui.QPixmap.fromImage(qimg)
        if state:
            tr = QtCore.Qt.TransformationMode.SmoothTransformation
        else:
            tr = QtCore.Qt.TransformationMode.FastTransformation
        return qpixmap.scaled(
            self.width(), self.height(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, tr
        )


class QAutoContrastMenu(QtW.QMenu):
    def __init__(self, parent: QImageViewControl):
        super().__init__(parent)
        self._control = parent
        action = self.addAction("Live Auto Contrast", self._toggle_auto_contrast)
        action.setCheckable(True)
        action.setChecked(parent._auto_cont_live)

    def _toggle_auto_contrast(self):
        live = self._control._auto_cont_live = not self._control._auto_cont_live
        self._control._auto_cont_btn.setCheckable(live)
        self._control._auto_cont_btn.setChecked(live)
        if live:
            self._control._auto_contrast()


class QChannelToggleSwitch(QToggleSwitch):
    """Toggle switch for channel visibility."""

    def __init__(self, channel: ChannelInfo):
        super().__init__()
        self._channel_info = channel
        self.setChecked(True)

    def set_channel(self, channel: ChannelInfo):
        self._channel_info = channel
        self.setText(channel.name)
        self._channel_on_color = QtGui.QColor.fromRgbF(*channel.colormap(0.5))

    def drawGroove(self, painter, rect, option):
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        is_checked = option.state & QtW.QStyle.StateFlag.State_On
        painter.setBrush(self._channel_on_color if is_checked else option.off_color)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(0.65)
        painter.drawRect(rect)

    def drawHandle(self, painter, rect, option):
        painter.setPen(QtCore.Qt.PenStyle.SolidLine)
        is_checked = option.state & QtW.QStyle.StateFlag.State_On
        painter.setBrush(self._channel_on_color if is_checked else option.off_color)
        painter.setOpacity(1.0)
        painter.drawRect(rect)


class QChannelToggleSwitches(QtW.QScrollArea):
    stateChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        central = QtW.QWidget()
        layout = QtW.QGridLayout(central)
        layout.setContentsMargins(2, 2, 2, 2)
        self._layout = layout
        self._toggle_switches: list[QChannelToggleSwitch] = []
        self.setWidget(central)
        self._label_font = QtGui.QFont(DefaultFontFamily, 8)

    def set_channels(self, channels: list[ChannelInfo]):
        labels = [ch.name for ch in channels]
        for ith in range(len(self._toggle_switches), len(labels)):
            sw = QChannelToggleSwitch(channels[ith])
            sw.setChecked(True)
            sw.setFont(self._label_font)
            sw.toggled.connect(self._emit_state_changed)
            row, col = divmod(ith, 3)
            self._layout.addWidget(sw, row, col)
            self._toggle_switches.append(sw)
        while len(self._toggle_switches) > len(labels):
            sw = self._toggle_switches.pop()
            sw.setParent(None)
        for i in range(len(channels)):
            sw = self._toggle_switches[i]
            sw.set_channel(channels[i])
        self.setFixedWidth(70 * min(3, len(self._toggle_switches)) + 10)

    def _emit_state_changed(self):
        self.stateChanged.emit()

    def check_states(self) -> list[bool]:
        return [sw.isChecked() for sw in self._toggle_switches]

    def set_check_states(self, states: list[bool]):
        for sw, st in zip(self._toggle_switches, states):
            sw.setChecked(st)

    def has_channels(self) -> bool:
        return len(self._toggle_switches) > 0
