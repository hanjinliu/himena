from himena.consts import StandardType
from himena.widgets import SubWindow
from himena.plugins import register_function, configure_gui
from himena.types import Parametric
from himena.qt.magicgui import ColorEdit
from qtpy import QtGui
from cmap import Color
from .image import QImageView
from ._image_components._scale_bar import ScaleBarAnchor, ScaleBarType


### Commands specific to built-in widgets ###
@register_function(
    title="Scale bar ...",
    types=StandardType.IMAGE,
    menus="tools/image",
    command_id="builtins:image:setup-image-scale-bar",
)
def setup_image_scale_bar(win: SubWindow[QImageView]) -> Parametric:
    scale_bar = win.widget._img_view._scale_bar_widget

    @configure_gui(
        anchor={"value": scale_bar._anchor},
        type={"value": scale_bar._scale_bar_type},
        color={"widget_type": ColorEdit, "value": scale_bar._color.name()},
        preview=True,
    )
    def setup(
        visible: bool = True,
        text_visible: bool = True,
        anchor: ScaleBarAnchor = ScaleBarAnchor.BOTTOM_RIGHT,
        type: ScaleBarType = ScaleBarType.SHADOWED,
        color="white",
    ):
        qcolor = QtGui.QColor.fromRgbF(*Color(color).rgba)
        win.widget._img_view._scale_bar_widget.update_scale_bar(
            anchor=anchor, type=type, color=qcolor, visible=visible,
            text_visible=text_visible
        )  # fmt: skip

    return setup


@register_function(
    title="Set zoom factor ...",
    types=StandardType.IMAGE,
    menus="tools/image",
    command_id="builtins:image:set-zoom-factor",
)
def set_zoom_factor(win: SubWindow[QImageView]) -> Parametric:
    """Set the zoom factor of the canvas."""
    view = win.widget._img_view
    current_scale = view.transform().m11()

    @configure_gui(
        scale={
            "value": round(current_scale * 100, 2),
            "min": 0.001,
            "label": "Zoom (%)",
        }
    )
    def run_set_zoom(scale: float):
        ratio = scale / (current_scale * 100)
        view.scale_and_update_handles(ratio)

    return run_set_zoom
