from __future__ import annotations


from matplotlib.figure import Figure
from matplotlib.backends import backend_qtagg
from qtpy import QtWidgets as QtW, QtGui

from himena.plugins import validate_protocol
from himena.types import Size, WidgetDataModel
from himena.consts import StandardType
from himena.style import Theme
from himena.standards import plotting as hplt
from himena_builtins.qt.plot._conversion import convert_plot_layout, update_axis_props


class QMatplotlibCanvasBase(QtW.QWidget):
    __himena_widget_id__ = "builtins:QMatplotlibCanvasBase"
    __himena_display_name__ = "Matplotlib Canvas"

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._canvas: FigureCanvasQTAgg | None = None
        self._toolbar: backend_qtagg.NavigationToolbar2QT | None = None
        self._plot_models: hplt.BaseLayoutModel | None = None

    @property
    def figure(self) -> Figure:
        return self._canvas.figure

    @validate_protocol
    def control_widget(self) -> QtW.QWidget:
        return self._toolbar

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 300, 240

    @validate_protocol
    def widget_resized_callback(self, size_old, size_new: tuple[int, int]):
        if size_new[0] > 40 and size_new[1] > 40:
            self._canvas.figure.tight_layout()

    def _prep_toolbar(self, toolbar_class=backend_qtagg.NavigationToolbar2QT):
        if self._toolbar is not None:
            return self._toolbar
        toolbar = toolbar_class(self._canvas, self)
        spacer = QtW.QWidget()
        toolbar.insertWidget(toolbar.actions()[0], spacer)
        return toolbar

    # FIXME: cannot correctly determine the icon color in Qt6
    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        if self._toolbar is None:
            return

        icon_color = (
            QtGui.QColor(0, 0, 0)
            if theme.is_light_background()
            else QtGui.QColor(255, 255, 255)
        )
        for toolbtn in self._toolbar.findChildren(QtW.QToolButton):
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


class QMatplotlibCanvas(QMatplotlibCanvasBase):
    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        was_none = self._canvas is None
        if was_none:
            self._canvas = FigureCanvasQTAgg(model.value)
            self.layout().addWidget(self._canvas)
            self._toolbar = self._prep_toolbar()
        if isinstance(model.value, Figure):
            if not was_none:
                raise ValueError("Figure is already set")
        else:
            raise ValueError(f"Unsupported model: {model.value}")
        if was_none:
            self._toolbar.pan()
            self._canvas.figure.tight_layout()

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
    __himena_widget_id__ = "builtins:QModelMatplotlibCanvas"
    __himena_display_name__ = "Built-in Plot Canvas"

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        was_none = self._canvas is None
        if was_none:
            self._canvas = FigureCanvasQTAgg()
            self.layout().addWidget(self._canvas)
            self._toolbar = self._prep_toolbar(QNavigationToolBar)
        if isinstance(model.value, hplt.BaseLayoutModel):
            self._plot_models = convert_plot_layout(model.value, self.figure)
            self._canvas.draw()
        else:
            raise ValueError(f"Unsupported model: {model.value}")
        if was_none and not isinstance(self._plot_models, hplt.SingleAxes3D):
            self._toolbar.pan()

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
            update_axis_props(model_axes, mpl_axes)
        return WidgetDataModel(
            value=value,
            type=self.model_type(),
            extension_default=".plot.json",
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.PLOT

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
        self._plot_models = model.value.merge_with(self._plot_models)
        convert_plot_layout(self._plot_models, self.figure)
        self._canvas.draw()

    @validate_protocol
    def allowed_drop_types(self) -> list[str]:
        return [StandardType.PLOT]

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 300, 240

    @validate_protocol
    def widget_resized_callback(self, size_old: Size, size_new: Size):
        if size_new.width > 40 and size_new.width > 40:
            self._canvas.figure.tight_layout()

    @validate_protocol
    def widget_added_callback(self):
        self._canvas.figure.tight_layout()


# remove some of the tool buttons
class QNavigationToolBar(backend_qtagg.NavigationToolbar2QT):
    toolitems = (
        ("Home", "Reset original view", "home", "home"),
        ("Back", "Back to previous view", "back", "back"),
        ("Forward", "Forward to next view", "forward", "forward"),
        (None, None, None, None),
        (
            "Pan",
            "Left button pans, Right button zooms\n"
            "x/y fixes axis, CTRL fixes aspect",
            "move",
            "pan",
        ),
        ("Zoom", "Zoom to rectangle\nx/y fixes axis", "zoom_to_rect", "zoom"),
        (None, None, None, None),
        ("Save", "Save the figure", "filesave", "save_figure"),
    )


class FigureCanvasQTAgg(backend_qtagg.FigureCanvasQTAgg):
    def mouseDoubleClickEvent(self, event):
        self.figure.tight_layout()
        self.draw()
        return super().mouseDoubleClickEvent(event)


FigureCanvas = FigureCanvasQTAgg


# The plt.show function will be overwriten to this.
# Modified from matplotlib_inline (BSD 3-Clause "New" or "Revised" License)
# https://github.com/ipython/matplotlib-inline
def show(close=True, block=None):
    import matplotlib.pyplot as plt
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
