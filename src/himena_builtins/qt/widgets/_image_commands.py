from typing import Literal, TypedDict

from qtpy import QtGui, QtCore
from cmap import Color
from magicgui.types import Undefined
from magicgui.type_map import register_type
from magicgui.widgets import ComboBox, TupleEdit, Container
from magicgui.widgets.bases import ValuedContainerWidget

from himena.consts import StandardType, MenuId
from himena.exceptions import Cancelled
from himena.widgets import SubWindow, MainWindow
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, Rect
from himena.standards import roi as _roi
from himena.utils import image_utils
from himena.qt.magicgui import ColorEdit, get_type_map, FloatEdit, ToggleSwitch
from himena import anchor

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
    """Set up the scale bar for the image viewer."""
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
    title="Capture Setting ...",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image:capture-setting",
    group="00-capture",
)
def capture_setting(ui: MainWindow) -> Parametric:
    """Open the setting of image capture."""
    capture = ImageViewCapture.get_instance(ui)

    @configure_gui(
        auto_close=False,
        title="Capture Setting",
        scale_bars={"value": capture._scale_bars.copy(), "layout": "vertical"},
    )
    def run(
        scale_bars: list[ScaleBarSpecDict],
    ):
        capture._scale_bars = scale_bars.copy()
        return

    return run


@register_function(
    title="Copy slice to clipboard",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image:copy-slice-to-clipboard",
    group="00-capture",
)
def copy_slice_to_clipboard(win: SubWindow[QImageView], ui: MainWindow):
    """Copy the current slice to the clipboard as is."""
    qimage = ImageViewCapture.get_instance(ui).to_qimage(win.widget)
    QtGui.QGuiApplication.clipboard().setImage(qimage)
    ui.show_notification("Image slice copied to the clipboard.", duration=3)


@register_function(
    title="Save slice to clipboard",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image:save-slice",
    group="00-capture",
)
def save_slice(win: SubWindow[QImageView], ui: MainWindow):
    """Save the current slice to file as is."""
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".png",
        allowed_extensions=[".png", ".jpg", ".jpeg"],
        caption="Save slice to clipboard",
    ):
        qimage = ImageViewCapture.get_instance(ui).to_qimage(win.widget)
        qimage.save(str(path))
    return None


@register_function(
    title="Copy viewer screenshot",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image:copy-viewer-screenshot",
    group="10-screenshot",
)
def copy_image_view_screenshot(win: SubWindow[QImageView], ui: MainWindow):
    """Copy the screenshot of the image view to the clipboard."""
    qimage = win.widget._img_view.grab().toImage()
    QtGui.QGuiApplication.clipboard().setImage(qimage)
    ui.show_notification("Image view screenshot copied to the clipboard.", duration=3)


@register_function(
    title="Save viewer screenshot",
    types=StandardType.IMAGE,
    menus=[MenuId.TOOLS_IMAGE_CAPTURE, "/model_menu/capture"],
    command_id="builtins:image:save-viewer-screenshot",
    group="10-screenshot",
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


class ImageViewCapture:
    _instances: "dict[int, ImageViewCapture]" = {}

    def __init__(self):
        self._scale_bars: list[ScaleBarSpecDict] = []

    @classmethod
    def get_instance(cls, ui: MainWindow) -> "ImageViewCapture":
        if (self := cls._instances.get(id(ui))) is None:
            self = cls()
            cls._instances[id(ui)] = self
        return self

    def to_qimage(self, view: QImageView) -> QtGui.QImage:
        if isinstance(current_roi := view.current_roi(), _roi.RectangleRoi):
            bbox = image_utils.roi_2d_to_bbox(current_roi, view._arr, view._is_rgb)
        else:
            bbox = Rect(0, 0, view._arr.shape[-1], view._arr.shape[-2])
        # manually paint the graphics items
        qimage = QtGui.QImage(
            bbox.width, bbox.height, QtGui.QImage.Format.Format_RGBA8888
        )
        painter = QtGui.QPainter(qimage)
        target_rect = QtCore.QRect(0, 0, bbox.width, bbox.height)
        source_rect = QtCore.QRect(bbox.left, bbox.top, bbox.width, bbox.height)
        for graphics in view._img_view._image_widgets:
            if graphics.isVisible():
                graphics.initPainter(painter)
                painter.drawImage(target_rect, graphics._qimage.copy(source_rect))

        # draw scale bars
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for sbar in self._scale_bars:
            width, height = sbar["shape"]
            axes = view.dims_slider.to_dim_axes()
            w_scale, h_scale = axes[-1].scale, axes[-2].scale
            w_px = int(round(width / w_scale))
            h_px = int(round(height / h_scale))
            qcolor = QtGui.QColor.fromRgbF(*Color(sbar["color"]).rgba)
            if rect := to_anchor_object(sbar, w_px, h_px).apply_anchor(
                bbox.size(), (w_px, h_px)
            ):
                painter.setBrush(qcolor)
                painter.drawRect(rect.left, rect.top, rect.width, rect.height)

        painter.end()
        return qimage


class ScaleBarSpecDict(TypedDict):
    shape: tuple[float, float]
    color: str
    anchor_pos: Literal["top-left", "top-right", "bottom-left", "bottom-right"]
    offset: "tuple[int, int] | None" = None


def to_anchor_object(
    sdict: ScaleBarSpecDict,
    w_px: int,
    h_px: int,
) -> anchor.WindowAnchor:
    anc_cls = anchor.type_to_anchor_class(sdict["anchor_pos"] + "-const")
    offset = sdict.get("offset")
    if offset is None:
        offset = (max(min(w_px, h_px), 1),) * 2
    return anc_cls(*offset)


class ScaleBarSpecWidget(ValuedContainerWidget[ScaleBarSpecDict]):
    def __init__(self, value=Undefined, **kwargs):
        self._width = FloatEdit(
            value=5,
            min=0,
            label="width",
            tooltip="Scale bar width in the unit of the image scale",
        )
        self._height = FloatEdit(
            value=0.5,
            min=0,
            label="height",
            tooltip="Scale bar height in the unit of the image scale",
        )
        self._color = ColorEdit(
            "white", label="color", tooltip="color of the scale bar"
        )
        self._anchor_pos = ComboBox(
            value="bottom-right",
            choices=["top-left", "top-right", "bottom-left", "bottom-right"],
            label="anchor",
        )
        self._use_offset = ToggleSwitch(value=False, text="Constant offset")
        self._offset = TupleEdit(value=(10, 10), label="offset (pixels)")
        c0 = Container(widgets=[self._width, self._height], layout="horizontal")
        c1 = Container(widgets=[self._anchor_pos, self._color], layout="horizontal")
        c2 = Container(widgets=[self._offset, self._use_offset], layout="horizontal")
        c0.margins = c1.margins = c2.margins = (0, 0, 0, 0)
        super().__init__(
            value=value,
            widgets=[c0, c1, c2],
            **kwargs,
        )
        for wd in [
            self._width,
            self._height,
            self._color,
            self._anchor_pos,
            self._use_offset,
            self._offset,
        ]:
            wd.changed.connect(self._on_changed)
        self._use_offset.changed.connect(self._use_offset_changed)
        self._use_offset_changed(self._use_offset.value)

    def _use_offset_changed(self, use_offset: bool):
        self._offset.enabled = use_offset

    def _on_changed(self):
        self.changed.emit(self.get_value())

    def get_value(self):
        return {
            "shape": (self._width.value, self._height.value),
            "color": self._color.get_value().hex,
            "anchor_pos": self._anchor_pos.value,
            "offset": self._offset.value if self._use_offset.value else None,
        }

    def set_value(self, val):
        if val == Undefined:
            return
        val = ScaleBarSpecDict(**val)
        self._width.value, self._height.value = val["shape"]
        self._color.value = Color(val["color"]).hex
        self._anchor_pos.value = val["anchor_pos"]
        self._use_offset.value = val["offset"] is not None
        if self._use_offset.value:
            self._offset.value = val["offset"]


type_map = get_type_map()
type_map.register_type(ScaleBarSpecDict, widget_type=ScaleBarSpecWidget)
register_type(ScaleBarSpecDict, widget_type=ScaleBarSpecWidget)
