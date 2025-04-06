from himena.consts import StandardType, MenuId
from himena.exceptions import Cancelled
from himena.widgets import SubWindow, MainWindow
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, Rect
from himena.standards import roi as _roi
from himena.utils import image_utils
from himena.qt.magicgui import ColorEdit

from qtpy import QtGui, QtCore
from cmap import Color
from .image import QImageView
from ._image_components._scale_bar import ScaleBarAnchor, ScaleBarType


### Commands specific to built-in widgets ###
@register_function(
    title="Scale bar ...",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE],
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
    menus=[MenuId.TOOLS_IMAGE],
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


@register_function(
    title="Copy slice to clipboard",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image-capture:copy-slice-to-clipboard",
)
def copy_slice_to_clipboard(win: SubWindow[QImageView]):
    """Copy the current slice to the clipboard as is."""
    qimage = _get_qimage_of_current_slice(win.widget)
    QtGui.QGuiApplication.clipboard().setImage(qimage)
    return None


@register_function(
    title="Save slice to clipboard",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image-capture:save-slice",
)
def save_slice(win: SubWindow[QImageView], ui: MainWindow):
    """Save the current slice to file as is."""
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".png",
        allowed_extensions=[".png", ".jpg", ".jpeg"],
        caption="Save slice to clipboard",
    ):
        qimage = _get_qimage_of_current_slice(win.widget)
        qimage.save(str(path))
    return None


def _get_qimage_of_current_slice(view: QImageView) -> QtGui.QImage:
    if isinstance(current_roi := view.current_roi(), _roi.RectangleRoi):
        bbox = image_utils.roi_2d_to_bbox(current_roi, view._arr, view._is_rgb)
    else:
        bbox = Rect(0, 0, view._arr.shape[-1], view._arr.shape[-2])
    # manually paint the graphics items and copy the image to the clipboard
    qimage = QtGui.QImage(bbox.width, bbox.height, QtGui.QImage.Format.Format_RGBA8888)
    painter = QtGui.QPainter(qimage)
    target_rect = QtCore.QRect(0, 0, bbox.width, bbox.height)
    source_rect = QtCore.QRect(bbox.left, bbox.top, bbox.width, bbox.height)
    for graphics in view._img_view._image_widgets:
        if graphics.isVisible():
            graphics.initPainter(painter)
            painter.drawImage(target_rect, graphics._qimage.copy(source_rect))
    painter.end()
    return qimage


@register_function(
    title="Copy viewer screenshot",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image-screenshot:copy-viewer-screenshot",
)
def copy_image_view_screenshot(win: SubWindow[QImageView]):
    """Copy the screenshot of the image view to the clipboard."""
    qimage = win.widget._img_view.grab().toImage()
    QtGui.QGuiApplication.clipboard().setImage(qimage)


@register_function(
    title="Save viewer screenshot",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image-screenshot:save-viewer-screenshot",
)
def save_image_view_screenshot(win: SubWindow[QImageView], ui: MainWindow):
    """Save the screenshot of the image view to a file."""
    qimage = win.widget._img_view.grab().toImage()

    if file_path := ui.exec_file_dialog(
        mode="w",
        extension_default=".png",
        allowed_extensions=[".png", ".jpg", ".jpeg"],
        caption="Save image view screenshot",
    ):
        return qimage.save(str(file_path))
    raise Cancelled
