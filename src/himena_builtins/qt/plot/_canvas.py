from __future__ import annotations

from matplotlib.figure import Figure
from matplotlib.backends import backend_qtagg
import matplotlib.pyplot as plt
from qtpy import QtWidgets as QtW, QtGui, QtCore

from himena.plugins import validate_protocol
from himena.types import DropResult, Size, WidgetDataModel
from himena.consts import StandardType
from himena.style import Theme
from himena.standards import plotting as hplt
from himena.standards.model_meta import DimAxis
from himena_builtins.qt.plot._conversion import (
    convert_plot_layout,
    update_model_axis_by_mpl,
    convert_plot_model,
)
from himena_builtins.qt.plot._config import MatplotlibCanvasConfigs
from himena_builtins.qt.widgets._dim_sliders import QDimsSlider

TIGHT_LAYOUT_PAD = 1.02


class QMatplotlibCanvasBase(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._canvas: FigureCanvasQTAgg | None = None
        self._toolbar: backend_qtagg.NavigationToolbar2QT | None = None
        self._plot_models: hplt.BaseLayoutModel | None = None
        self._modified = False
        self._cfg = MatplotlibCanvasConfigs()
        self._last_mouse_pos = QtCore.QPoint()
        self._current_theme: Theme | None = None

    @property
    def figure(self) -> Figure:
        """The internal Matplotlib figure object."""
        return self._canvas.figure

    @validate_protocol
    def control_widget(self) -> QtW.QWidget:
        if self._toolbar is None:
            self._toolbar = self._prep_toolbar()
        return self._toolbar

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 300, 240

    @validate_protocol
    def widget_resized_callback(self, size_old: Size, size_new: Size):
        if size_new.width > 40 and size_new.height > 40:
            self._canvas.figure.tight_layout(pad=TIGHT_LAYOUT_PAD)

    def _construct_toolbar(self):
        return QNavigationToolBar(self._canvas, self)

    def _prep_toolbar(self):
        toolbar = self._construct_toolbar()
        spacer = QtW.QWidget()
        toolbar.insertWidget(toolbar.actions()[0], spacer)

        # Don't switch to pan mode for 3D plots
        if not any(ax.name == "3d" for ax in self._canvas.figure.axes):
            toolbar.pan()
        self._update_toolbar_theme(toolbar)
        return toolbar

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        self._current_theme = theme
        if self._toolbar is None:
            return
        self._update_toolbar_theme(self._toolbar)

    def _update_toolbar_theme(self, toolbar: QtW.QWidget):
        if self._current_theme is None:
            return
        icon_color = (
            QtGui.QColor(0, 0, 0)
            if self._current_theme.is_light_background()
            else QtGui.QColor(255, 255, 255)
        )
        for toolbtn in toolbar.findChildren(QtW.QToolButton):
            assert isinstance(toolbtn, QtW.QToolButton)
            icon = toolbtn.icon()
            pixmap = icon.pixmap(100, 100)
            mask = pixmap.mask()
            pixmap.fill(icon_color)
            pixmap.setMask(mask)
            icon_new = QtGui.QIcon(pixmap)
            toolbtn.setIcon(icon_new)
            # Setting icon to the action as well; otherwise checking/unchecking will
            # revert the icon to the original color
            toolbtn.actions()[0].setIcon(icon_new)

    def _init_canvas(self, figure: Figure | None = None):
        self._canvas = FigureCanvasQTAgg(figure)
        self._canvas.contextmenu_requested.connect(self._show_context_menu)
        self.layout().addWidget(self._canvas)
        self._canvas.figure.tight_layout(pad=TIGHT_LAYOUT_PAD)

    def _make_context_menu(self) -> QtW.QMenu:
        menu = QtW.QMenu(self)
        menu.setTitle("Matplotlib Canvas")
        if self._toolbar is not None:
            action = menu.addAction("Reset original view")
            action.triggered.connect(self._toolbar.home)
            action = menu.addAction("Back to previous view")
            action.triggered.connect(self._toolbar.back)
            action = menu.addAction("Forward to next view")
            action.triggered.connect(self._toolbar.forward)
        menu.addSeparator()
        action = menu.addAction("Copy to clipboard")
        action.triggered.connect(self._copy_canvas)
        if self._toolbar is not None:
            action = menu.addAction("Save figure")
            action.triggered.connect(self._toolbar.save_figure)
        return menu

    def _show_context_menu(self, pos: QtCore.QPoint):
        self._make_context_menu().exec(pos)

    def _copy_canvas(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        image = self._canvas.grab()
        clipboard.setPixmap(image, QtGui.QClipboard.Mode.Clipboard)


class QMatplotlibCanvas(QMatplotlibCanvasBase):
    """A widget that displays a Matplotlib figure itself."""

    __himena_widget_id__ = "builtins:QMatplotlibCanvasBase"
    __himena_display_name__ = "Matplotlib Canvas"

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        was_none = self._canvas is None
        if isinstance(model.value, Figure):
            if was_none:
                self._init_canvas(model.value)
            else:
                raise ValueError("Cannot update the figure of an existing canvas")
        else:
            raise ValueError(f"Unsupported model: {model.value}")

    def _construct_toolbar(self):
        """Use the native toolbar."""
        return backend_qtagg.NavigationToolbar2QT(self._canvas, self)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.figure,
            type=self.model_type(),
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.MPL_FIGURE


class QModelMatplotlibCanvas(QMatplotlibCanvasBase):
    """A widget that displays himena standard plot models in a Matplotlib figure.

    The internal data structure is follows the himena standard.

    ## Basic Usage

    - Mouse interactivity can be controlled in the toolbar.
    - Double-click the canvas to adjust the layout.
    - This widget accepts dropping another plot model. The dropped model will be merged.

    """

    __himena_widget_id__ = "builtins:QModelMatplotlibCanvas"
    __himena_display_name__ = "Built-in Plot Canvas"

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        was_none = self._canvas is None
        _assert_plot_model(model.value)
        if was_none:
            self._init_canvas()
        with plt.style.context(self._cfg.to_dict()):
            self._plot_models = convert_plot_layout(model.value, self.figure)
        self._canvas.draw()

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        value = self._plot_models.model_copy()
        # TODO: update the model with the current canvas state as much as possible
        if isinstance(value, hplt.SingleAxes):
            model_axes_ref = [value.axes]
        elif isinstance(value, hplt.layout.Layout1D):
            model_axes_ref = value.axes
        elif isinstance(value, hplt.layout.Grid):
            model_axes_ref = sum(value.axes, [])
        elif isinstance(value, hplt.SingleAxes3D):
            model_axes_ref = [value.axes]
        else:
            model_axes_ref = []  # Not implemented
        mpl_axes_ref = self.figure.axes
        for model_axes, mpl_axes in zip(model_axes_ref, mpl_axes_ref):
            update_model_axis_by_mpl(model_axes, mpl_axes)
        return WidgetDataModel(
            value=value,
            type=self.model_type(),
            extension_default=".plot.json",
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.PLOT

    @validate_protocol
    def update_configs(self, cfg: MatplotlibCanvasConfigs):
        self._cfg = cfg

    @validate_protocol
    def dropped_callback(self, model: WidgetDataModel):
        if not (
            isinstance(model.value, hplt.BaseLayoutModel)
            and isinstance(self._plot_models, hplt.BaseLayoutModel)
        ):
            raise ValueError(
                f"Both models must be BaseLayoutModel, got {model.value!r} and "
                f"{self._plot_models!r}"
            )
        return DropResult(
            command_id="builtins:plot:concatenate-with", with_params={"others": [model]}
        )

    @validate_protocol
    def allowed_drop_types(self) -> list[str]:
        return [StandardType.PLOT]

    @validate_protocol
    def widget_added_callback(self):
        self._canvas.figure.tight_layout(pad=TIGHT_LAYOUT_PAD)

    @validate_protocol
    def is_modified(self) -> bool:
        return self._modified

    @validate_protocol
    def set_modified(self, value: bool):
        self._modified = value


class QModelMatplotlibCanvasStack(QMatplotlibCanvasBase):
    __himena_widget_id__ = "builtins:QModelMatplotlibCanvasStack"
    __himena_display_name__ = "Built-in Plot Canvas Stack"
    _plot_models: hplt.SingleStackedAxes | None

    def __init__(self):
        super().__init__()
        self._dims_slider = QDimsSlider()
        self._dims_slider.valueChanged.connect(self._slider_changed)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        was_none = self._canvas is None
        if not isinstance(model.value, hplt.SingleStackedAxes):
            raise ValueError(
                f"Expected a SingleStackedAxes model, got {type(model.value)}"
            )
        if was_none:
            self._init_canvas()
            self.layout().addWidget(self._dims_slider)

        self._dims_slider.set_dimensions(
            model.value.shape + (0, 0),
            axes=model.value.axes.multi_dims + [DimAxis(name=""), DimAxis(name="")],
        )
        with plt.style.context(self._cfg.to_dict()):
            self._plot_models = convert_plot_layout(model.value, self.figure)
        self._slider_changed(self._dims_slider.value(), auto_scale=False)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        value = self._plot_models.model_copy()
        if not isinstance(value, hplt.SingleStackedAxes):
            raise ValueError("The model is not a SingleAxesStack")
        mpl_axes_ref = self.figure.axes
        model_axes_ref = [value.axes]
        for model_axes, mpl_axes in zip(model_axes_ref, mpl_axes_ref):
            update_model_axis_by_mpl(model_axes, mpl_axes)
        return WidgetDataModel(
            value=value,
            type=self.model_type(),
            extension_default=".plot.json",
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.PLOT_STACK

    @validate_protocol
    def update_configs(self, cfg: MatplotlibCanvasConfigs):
        self._cfg = cfg

    def _slider_changed(self, value: int, *, auto_scale: bool = True):
        if self._plot_models is None:
            return
        if not isinstance(self._plot_models, hplt.SingleStackedAxes):
            raise ValueError("The model is not a SingleAxesStack")
        axes_component = self._plot_models.axes[value]
        ax_mpl = self.figure.axes[0]
        xlim = ax_mpl.get_xlim()
        ylim = ax_mpl.get_ylim()
        ax_mpl.clear()
        for model in axes_component.models:
            convert_plot_model(model, ax_mpl)
        if auto_scale:
            ax_mpl.set_xlim(xlim)
            ax_mpl.set_ylim(ylim)
        self._canvas.draw()


def _assert_plot_model(val):
    """Check if the value is a plot model."""
    if not isinstance(val, hplt.BaseLayoutModel):
        raise TypeError(f"Expected a plot model, got {type(val)}")


# remove some of the tool buttons
class QNavigationToolBar(backend_qtagg.NavigationToolbar2QT):
    toolitems = (
        ("Home", "Reset original view", "home", "home"),
        ("Back", "Back to previous view", "back", "back"),
        ("Forward", "Forward to next view", "forward", "forward"),
        (None, None, None, None),
        (
            "Pan",
            "Left button pans, Right button zooms\nx/y fixes axis, CTRL fixes aspect",
            "move",
            "pan",
        ),
        ("Zoom", "Zoom to rectangle\nx/y fixes axis", "zoom_to_rect", "zoom"),
        (None, None, None, None),
        ("Save", "Save the figure", "filesave", "save_figure"),
    )


class FigureCanvasQTAgg(backend_qtagg.FigureCanvasQTAgg):
    contextmenu_requested = QtCore.Signal(QtCore.QPoint)
    _last_mouse_pos = QtCore.QPoint()

    def mouseDoubleClickEvent(self, event):
        self.figure.tight_layout(pad=TIGHT_LAYOUT_PAD)
        self.draw()
        return super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, a0):
        self._last_mouse_pos = a0.pos()
        return super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent):
        if (self._last_mouse_pos - a0.pos()).manhattanLength() < 8:
            if a0.button() == QtCore.Qt.MouseButton.RightButton:
                self.contextmenu_requested.emit(self.mapToGlobal(a0.pos()))
        self._last_mouse_pos = QtCore.QPoint()
        return super().mouseReleaseEvent(a0)


FigureCanvas = FigureCanvasQTAgg


# The plt.show function will be overwriten to this.
# Modified from matplotlib_inline (BSD 3-Clause "New" or "Revised" License)
# https://github.com/ipython/matplotlib-inline
def show(close=True, block=None):
    from matplotlib._pylab_helpers import Gcf
    from himena.widgets import current_instance

    ui = current_instance()

    try:
        for figure_manager in Gcf.get_all_fig_managers():
            ui.add_object(
                figure_manager.canvas.figure,
                type=StandardType.MPL_FIGURE,
                title="Plot",
            )
    finally:
        show._called = True
        if close and Gcf.get_all_fig_managers():
            plt.close("all")


show._called = False
