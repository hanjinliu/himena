from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING
import numpy as np
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from superqt import QLabeledDoubleSlider, QToggleSwitch, QElidingLabel
from superqt.utils import qthrottled

from himena.consts import DefaultFontFamily
from himena.qt import qsignal_blocker, ndarray_to_qimage, QColoredToolButton
from himena.qt._qlineedit import QDoubleLineEdit
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


class QZoomInView(QtW.QLabel):
    def __init__(self):
        super().__init__()
        self.setToolTip(
            "Local Zoom-in View. While moving the mouse over the image, all the items\n"
            "except for the ROI handles are drawn here."
        )
        self._enabled = True
        self._local_size = 5
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

    def resizeEvent(self, a0):
        self.setFixedWidth(self.height())
        return super().resizeEvent(a0)

    def init(self):
        pixmap = self._make_pixmap(self.height(), enabled=self._enabled)
        self.setPixmap(pixmap)

    @lru_cache(maxsize=4)
    def _make_pixmap(self, size: int, enabled: bool) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QtGui.QColor(128, 128, 128, 63))
        c = self.width() / 2
        r = self.width() / 3
        painter.drawEllipse(QtCore.QRectF(c - r, c - r, 2 * r, 2 * r))
        if not enabled:
            painter.drawLine(QtCore.QPointF(c - r, c - r), QtCore.QPointF(c + r, c + r))
            painter.drawLine(QtCore.QPointF(c - r, c + r), QtCore.QPointF(c + r, c - r))
        painter.end()
        return pixmap

    def _make_menu(self):
        menu = QtW.QMenu(self)
        action = menu.addAction(
            "Zoom-in View Enabled",
            self._toggle_enabled,
        )
        action.setCheckable(True)
        action.setChecked(self._enabled)
        menu.addSeparator()
        for i in [3, 5, 7, 11, 17, 25]:
            s1 = i
            act = menu.addAction(f"{i} x {i}", lambda s=s1: self._set_size(s))
            act.setCheckable(True)
            act.setChecked(s1 == self._local_size)
        return menu

    def _show_menu(self, *_):
        menu = self._make_menu()
        menu.exec(QtGui.QCursor.pos())

    def _toggle_enabled(self):
        self._enabled = not self._enabled
        if not self._enabled:
            self.init()

    def _set_size(self, size: int):
        self._local_size = size


class QImageViewControlBase(QtW.QWidget):
    def __init__(self, image_view: QImageViewBase):
        super().__init__()
        self._zoom_view = QZoomInView()
        self._image_view = image_view
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._interp_check_box = QInterpolationSwitch(self)
        self._interp_check_box.toggled.connect(self._interpolation_changed)

        self._hover_info = QElidingLabel()
        self._hover_info.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._hover_info.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._hover_info.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        for wdt in self._widgets_to_add():
            layout.addWidget(wdt)

    def _widgets_to_add(self) -> list[QtW.QWidget]:
        return [self._hover_info, self._zoom_view, self._interp_check_box]

    def _interpolation_changed(self, checked: bool):
        self._image_view._img_view.setSmoothing(checked)

    def update_rgb_channel_dtype(self, is_rgb: bool, nchannels: int, dtype):
        pass

    def _set_zoom_view(self, pos: QtCore.QPointF | None):
        if pos is None or not self._zoom_view._enabled:
            self._zoom_view.init()
        else:
            # Render local zoom view around cursor
            zoom_size = self._zoom_view.height()
            local_size = self._zoom_view._local_size
            zoom_factor = zoom_size / local_size  # magnification factor

            # Define the region to capture in scene coordinates
            rect = QtCore.QRectF(
                pos.x() - local_size / 2,
                pos.y() - local_size / 2,
                local_size,
                local_size,
            )

            # Create a pixmap to render the zoomed region
            render_size = int(zoom_size * self.devicePixelRatioF())
            pixmap = QtGui.QPixmap(render_size, render_size)
            pixmap.setDevicePixelRatio(self.devicePixelRatioF())
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

            # Render items individually, excluding selection handles
            for item in self._image_view._img_view.iter_items_except_handles(rect):
                painter.save()
                painter.setTransform(
                    QtGui.QTransform.fromScale(zoom_factor, zoom_factor)
                )
                painter.translate(-rect.x(), -rect.y())
                item.paint(painter, QtW.QStyleOptionGraphicsItem(), None)
                painter.restore()

            painter.end()
            self._zoom_view.setPixmap(pixmap)


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

        self._auto_cont_btn = QAutoContrastButton(self._auto_contrast)

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
            self._hover_info, self._zoom_view, self._cmp_mode_combo, self._chn_vis,
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
        minmax = self._histogram.calc_contrast_limits(*self._auto_cont_btn.qminmax)
        if minmax is None:
            return
        min_new, max_new = minmax

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
    def __init__(self, parent: QAutoContrastButton):
        super().__init__(parent)
        self._btn = parent
        action = self.addAction("Live Auto Contrast", self._toggle_live_auto_contrast)
        action.setCheckable(True)
        action.setChecked(parent._auto_cont_live)

        min_widget = QDoubleLineEdit(format(parent._qmin * 100, ".2f"))
        min_widget.setMinimum(0.0)
        min_widget.setMaximum(100.0)
        ac_min = QtW.QWidgetAction(self)
        ac_min.setDefaultWidget(_labeled("Min %", min_widget))
        max_widget = QDoubleLineEdit(format(parent._qmax * 100, ".2f"))
        ac_max = QtW.QWidgetAction(self)
        max_widget.setMinimum(0.0)
        max_widget.setMaximum(100.0)
        ac_max.setDefaultWidget(_labeled("Max %", max_widget))

        @min_widget.valueChanged.connect
        def _on_min_changed(txt: str):
            val = float(txt) / 100
            _qmin, _qmax = parent.qminmax
            _qmin = val
            if val > _qmax:
                _qmax = val
                max_widget.setText(min_widget.text())
            parent.qminmax = _qmin, _qmax

        @max_widget.valueChanged.connect
        def _on_max_changed(txt: str):
            val = float(txt) / 100
            _qmin, _qmax = parent.qminmax
            _qmax = val
            if val < _qmin:
                _qmin = val
                min_widget.setText(max_widget.text())
            parent.qminmax = _qmin, _qmax

        self.addAction(ac_min)
        self.addAction(ac_max)
        self._min_edit = min_widget
        self._max_edit = max_widget

    def _toggle_live_auto_contrast(self):
        live = self._btn._auto_cont_live = not self._btn._auto_cont_live
        self._btn.setCheckable(live)
        self._btn.setChecked(live)
        if live:
            self._btn._callback()


class QAutoContrastButton(QColoredToolButton):
    def __init__(self, callback):
        super().__init__(callback, ICON_PATH / "auto_contrast_once.svg")
        self.setToolTip("Auto Contrast (right click to change settings)")
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._exec_autocontrast_menu)
        self._auto_cont_live = False
        self._qmin = 0.0
        self._qmax = 1.0

    @property
    def live(self) -> bool:
        return self._auto_cont_live

    @property
    def qminmax(self) -> tuple[float, float]:
        qmin = max(self._qmin, 0.0)
        qmax = min(self._qmax, 1.0)
        return (qmin, qmax)

    @qminmax.setter
    def qminmax(self, qminmax: tuple[float, float]):
        self._qmin, self._qmax = qminmax

    def _exec_autocontrast_menu(self, *_):
        menu = QAutoContrastMenu(self)
        return menu.exec(QtGui.QCursor.pos())


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


def _labeled(label: str, widget: QtW.QWidget) -> QtW.QWidget:
    container = QtW.QWidget()
    layout = QtW.QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    lbl = QtW.QLabel(label)
    lbl.setFont(QtGui.QFont(DefaultFontFamily, 8))
    layout.addWidget(lbl)
    layout.addWidget(widget)
    return container


def _interp_hist(qmin: float, edges: np.ndarray, cum_value: np.ndarray):
    # len(edges) == len(cum_value)
    i = np.argmax(qmin <= cum_value)
    if i == len(edges) - 1:
        return edges[-1]
    return edges[i] + (edges[i + 1] - edges[i]) * (qmin - cum_value[i])
