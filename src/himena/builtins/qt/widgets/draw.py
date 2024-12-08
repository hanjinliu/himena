from __future__ import annotations

from enum import Enum, auto
from typing import NamedTuple
from qtpy import QtWidgets as QtW, QtGui, QtCore
from superqt import QIconifyIcon
import numpy as np

from himena.consts import StandardType
from himena.standards.model_meta import ArrayMeta
from himena.types import WidgetDataModel
from himena.plugins import protocol_override
from himena.qt._utils import ndarray_to_qimage, qimage_to_ndarray, ArrayQImage
from himena.qt._qcoloredit import QColorEdit
from himena._utils import UndoRedoStack


class DrawMode(Enum):
    DRAW = auto()
    ERASE = auto()
    PICK = auto()
    FILL = auto()


_TOP_LEFT = QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft


class PaintAction(NamedTuple):
    offset: tuple[int, int]
    old: np.ndarray
    new: np.ndarray


class PasetResizeAction(NamedTuple):
    old: np.ndarray
    new: np.ndarray


class QDrawCanvas(QtW.QScrollArea):
    """A built-in drawing canvas widget."""

    __himena_widget_id__ = "builtins:QDrawCanvas"
    __himena_display_name__ = "Built-in Drawing Canvas"

    def __init__(self):
        super().__init__()
        self._central_widget = QtW.QWidget()
        self.setWidget(self._central_widget)
        self.setAlignment(_TOP_LEFT)
        self.setWidgetResizable(True)
        self._mode = DrawMode.DRAW

        self._canvas_label = QtW.QLabel(self)
        self._canvas_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Fixed, QtW.QSizePolicy.Policy.Fixed
        )
        pixmap = QtGui.QPixmap(200, 200)
        pixmap.fill(QtCore.Qt.GlobalColor.white)
        self._set_pixmap(pixmap)

        _layout = QtW.QVBoxLayout(self._central_widget)
        _layout.setAlignment(_TOP_LEFT)
        _layout.addWidget(self._canvas_label)
        _layout.setContentsMargins(2, 2, 2, 2)
        self._last_pos: QtCore.QPoint | None = None
        self._is_modified = False
        self._is_editable = True
        self._pen = QtGui.QPen(
            QtCore.Qt.GlobalColor.black,
            2,
            cap=QtCore.Qt.PenCapStyle.RoundCap,
            join=QtCore.Qt.PenJoinStyle.RoundJoin,
        )
        self._control = QDrawCanvasControl(self)
        self._set_mode(self._mode)

        self._undo_redo_stack = UndoRedoStack[PaintAction | PasetResizeAction]()
        self._pixmap_before_paint = self._canvas_label.pixmap().copy()

    def _set_pixmap(self, pixmap: QtGui.QPixmap):
        self._canvas_label.setPixmap(pixmap)
        self._canvas_label.setFixedSize(pixmap.size())

    def _set_mode(self, mode: DrawMode):
        self._mode = mode
        if mode is DrawMode.PICK:
            self._canvas_label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        elif mode is DrawMode.FILL:
            self._canvas_label.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        else:
            self._canvas_label.setCursor(QtCore.Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._mode in (DrawMode.DRAW, DrawMode.ERASE, DrawMode.FILL):
                self._pixmap_before_paint = self._canvas_label.pixmap().copy()
            if self._mode in (DrawMode.DRAW, DrawMode.ERASE):
                self._draw(event.pos())
            elif self._mode is DrawMode.PICK:
                self.pick_color(event.pos())
                self._control._mode._set_mode(DrawMode.DRAW)
            elif self._mode is DrawMode.FILL:
                self.fill_backet(event.pos())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._mode not in (DrawMode.DRAW, DrawMode.ERASE):
                return
            self._draw(event.pos())

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._last_pos = None
        if self._mode in (DrawMode.DRAW, DrawMode.ERASE, DrawMode.FILL):
            self._add_paint_action_to_stack(
                self._pixmap_before_paint, self._canvas_label.pixmap()
            )
            self._pixmap_before_paint = self._canvas_label.pixmap().copy()

    def _draw(self, pos: QtCore.QPoint):
        is_point = False
        if self._last_pos is None:
            self._last_pos = pos
            is_point = True
        if not self._is_editable:
            return
        painter = QtGui.QPainter(self._canvas_label.pixmap())
        if self._mode is DrawMode.ERASE:
            pen = QtGui.QPen(QtCore.Qt.GlobalColor.white, self._pen.width())
            painter.setPen(pen)
        else:
            painter.setPen(self._pen)
        if is_point:
            painter.drawPoint(pos)
        else:
            painter.drawLine(self._last_pos, pos)
        self._last_pos = pos
        painter.end()
        self.update()
        self._is_modified = True

    def _add_paint_action_to_stack(
        self, old_pixmap: QtGui.QPixmap, new_pixmap: QtGui.QPixmap
    ):
        arr_before = qimage_to_ndarray(old_pixmap.toImage())
        arr_after = qimage_to_ndarray(new_pixmap.toImage())
        arr_diff = np.any(arr_before != arr_after, axis=-1)
        if not np.any(arr_diff):
            # nothing changed, no need to save the action
            return
        xdiff = np.any(arr_diff, axis=0)
        ydiff = np.any(arr_diff, axis=1)
        x0, x1 = np.where(xdiff)[0][[0, -1]]
        y0, y1 = np.where(ydiff)[0][[0, -1]]
        self._undo_redo_stack.push(
            PaintAction(
                offset=(y0, x0),
                old=arr_before[y0 : y1 + 1, x0 : x1 + 1],
                new=arr_after[y0 : y1 + 1, x0 : x1 + 1],
            )
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if (
            event.key() == QtCore.Qt.Key.Key_C
            and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            clipboard = QtGui.QGuiApplication.clipboard()
            clipboard.setPixmap(self._canvas_label.pixmap())
        elif (
            event.key() == QtCore.Qt.Key.Key_V
            and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            clipboard = QtGui.QGuiApplication.clipboard()
            self.paste_pixmap(clipboard.pixmap())
        elif (
            event.key() == QtCore.Qt.Key.Key_Z
            and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.undo()
        elif (
            event.key() == QtCore.Qt.Key.Key_Y
            and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.redo()

    def paste_pixmap(self, pixmap: QtGui.QPixmap):
        if pixmap.isNull():
            return
        incoming_size = pixmap.size()
        current_size = self._canvas_label.pixmap().size()
        old_pixmap = self._pixmap_before_paint
        if (
            incoming_size.width() > current_size.width()
            or incoming_size.height() > current_size.height()
        ):
            new_pixmap = QtGui.QPixmap(
                QtCore.QSize(
                    max(incoming_size.width(), current_size.width()),
                    max(incoming_size.height(), current_size.height()),
                )
            )
            painter = QtGui.QPainter(new_pixmap)
            painter.drawPixmap(0, 0, self._canvas_label.pixmap())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
        else:
            painter = QtGui.QPainter(self._canvas_label.pixmap())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
        self.update()
        new_pixmap = self._canvas_label.pixmap()
        self._undo_redo_stack.push(
            PasetResizeAction(
                old=qimage_to_ndarray(old_pixmap.toImage()),
                new=qimage_to_ndarray(new_pixmap.toImage()),
            )
        )
        self._pixmap_before_paint = self._canvas_label.pixmap().copy()
        self._is_modified = True

    def set_size(self, width: int, height: int):
        old_pixmap = self._canvas_label.pixmap().copy()
        new_pixmap = QtGui.QPixmap(width, height)
        new_pixmap.fill(QtCore.Qt.GlobalColor.white)
        painter = QtGui.QPainter(new_pixmap)
        painter.drawPixmap(0, 0, old_pixmap)
        painter.end()
        self._set_pixmap(new_pixmap)
        self._undo_redo_stack.push(
            PasetResizeAction(
                old=qimage_to_ndarray(old_pixmap.toImage()),
                new=qimage_to_ndarray(new_pixmap.toImage()),
            )
        )
        self._pixmap_before_paint = self._canvas_label.pixmap().copy()
        self._is_modified = True

    def pick_color(self, pos: QtCore.QPoint) -> None:
        color = QtGui.QColor(self._canvas_label.pixmap().toImage().pixel(pos))
        self._control._color.setColor(color)

    def fill_backet(self, pos: QtCore.QPoint) -> None:
        img = qimage_to_ndarray(self._canvas_label.pixmap().toImage())
        fill_color = self._pen.color().getRgb()
        seed_color = tuple(img[pos.y(), pos.x()])
        h, w = img.shape[:2]
        stack = [(pos.x(), pos.y())]
        old_pixmap = self._pixmap_before_paint
        while stack:
            x, y = stack.pop()
            if tuple(img[y, x]) != seed_color:
                continue
            img[y, x] = fill_color
            if 0 < x:
                stack.append((x - 1, y))
            if x < w - 1:
                stack.append((x + 1, y))
            if 0 < y:
                stack.append((x, y - 1))
            if y < h - 1:
                stack.append((x, y + 1))
        new_pixmap = QtGui.QPixmap.fromImage(ndarray_to_qimage(img))
        self._set_pixmap(new_pixmap)
        self._add_paint_action_to_stack(old_pixmap, new_pixmap)
        self._pixmap_before_paint = new_pixmap.copy()
        self._is_modified = True

    def undo(self):
        """Undo the last action."""
        if action := self._undo_redo_stack.undo():
            if isinstance(action, PasetResizeAction):
                self._undo_redo_paste_resize(action.old)
            else:
                self._undo_redo_paint(action.old, action.offset)
            self._update_undo_redo_buttons()

    def redo(self):
        """Redo the last action."""
        if action := self._undo_redo_stack.redo():
            if isinstance(action, PasetResizeAction):
                self._undo_redo_paste_resize(action.new)
            else:
                self._undo_redo_paint(action.new, action.offset)
            self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        self._control._btn_undo.setEnabled(self._undo_redo_stack.undoable())
        self._control._btn_redo.setEnabled(self._undo_redo_stack.redoable())

    def _undo_redo_paint(self, after: np.ndarray, offset: tuple[int, int]):
        arr = qimage_to_ndarray(self._canvas_label.pixmap().toImage())
        y0, x0 = offset
        y1, x1 = y0 + after.shape[0], x0 + after.shape[1]
        arr[y0:y1, x0:x1] = after
        pixmap = QtGui.QPixmap.fromImage(ndarray_to_qimage(arr))
        self._set_pixmap(pixmap)

    def _undo_redo_paste_resize(self, after: np.ndarray):
        pixmap = QtGui.QPixmap.fromImage(ndarray_to_qimage(after))
        self._set_pixmap(pixmap)

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        if model.value is None:
            return
        img = np.ascontiguousarray(model.value, dtype=np.uint8)
        pixmap = QtGui.QPixmap.fromImage(ndarray_to_qimage(img))
        self._set_pixmap(pixmap)
        self._control._size_label.setText(f"{img.shape[1]} px x {img.shape[0]} px")

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        img = ArrayQImage(self._canvas_label.pixmap().toImage())
        return WidgetDataModel(
            value=img,
            type=self.model_type(),
            metadata=ArrayMeta(current_indices=(0,)),
        )

    @protocol_override
    def model_type(self) -> str:
        return StandardType.IMAGE

    @protocol_override
    def control_widget(self) -> QtW.QWidget:
        return self._control

    @protocol_override
    def is_modified(self) -> bool:
        return self._is_modified

    @protocol_override
    def set_modified(self, modified: bool) -> None:
        self._is_modified = modified

    @protocol_override
    def is_editable(self) -> bool:
        return self._is_editable

    @protocol_override
    def set_editable(self, editable: bool) -> None:
        self._is_editable = editable

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return (
            min(400, self._canvas_label.width() + 28),
            min(400, self._canvas_label.height() + 28),
        )


class QDrawCanvasControl(QtW.QWidget):
    def __init__(self, canvas: QDrawCanvas):
        super().__init__()
        self._canvas = canvas
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._color = QColorEdit()
        self._color._color_swatch.setFixedSize(24, 20)
        self._color._line_edit.setFixedSize(60, 20)
        self._color.setColor(QtCore.Qt.GlobalColor.black)
        self._color.colorChanged.connect(self._on_color_changed)

        self._width = QtW.QSpinBox()
        self._width.setToolTip("Pen width")
        self._width.setRange(1, 20)
        self._width.setValue(2)
        self._width.setSuffix(" px")
        self._width.valueChanged.connect(self._on_width_changed)

        self._mode = QDrawModeButtons()
        self._mode._set_mode(DrawMode.DRAW)
        self._mode.modeChanged.connect(self._on_mode_changed)

        self._btn_undo = _tool_btn(
            icon_name="mdi:undo",
            tooltip="Undo",
            callback=self._canvas.undo,
        )
        self._btn_redo = _tool_btn(
            icon_name="mdi:redo",
            tooltip="Redo",
            callback=self._canvas.redo,
        )
        self._size_label = QtW.QLabel("200 px x 200 px")

        # The "set size" button
        self._btn_set_size = _tool_btn(
            icon_name="mdi:canvas",
            tooltip="Set size of the canvas",
        )
        self._btn_set_size.setPopupMode(
            QtW.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        _set_size_widget = QtW.QWidget()
        _size_widget_layout = QtW.QHBoxLayout(_set_size_widget)
        _size_widget_layout.setContentsMargins(0, 0, 0, 0)
        _size_widget_layout.addWidget(QtW.QLabel("Width:"))
        self._width_spin = QtW.QSpinBox()
        self._width_spin.setRange(10, 1000)
        self._width_spin.setValue(200)
        _size_widget_layout.addWidget(self._width_spin)
        _size_widget_layout.addWidget(QtW.QLabel("Height:"))
        self._height_spin = QtW.QSpinBox()
        self._height_spin.setRange(10, 1000)
        self._height_spin.setValue(200)
        _size_widget_layout.addWidget(self._height_spin)
        _btn_set_size_ok = QtW.QPushButton("OK")
        _btn_set_size_ok.clicked.connect(self._set_size)
        _btn_set_size_ok.setFixedWidth(32)
        _size_widget_layout.addWidget(_btn_set_size_ok)
        menu = QtW.QMenu()
        action = QtW.QWidgetAction(menu)
        action.setDefaultWidget(_set_size_widget)
        menu.addAction(action)
        self._btn_set_size.setMenu(menu)

        # add widgets to layout
        spacer = QtW.QWidget()
        _layout.addWidget(spacer)
        _layout.addWidget(self._size_label)
        _layout.addWidget(self._btn_set_size)
        _layout.addWidget(self._btn_undo)
        _layout.addWidget(self._btn_redo)
        _layout.addWidget(self._mode)
        _layout.addWidget(self._width)
        _layout.addWidget(self._color)

    def _on_color_changed(self, color: tuple):
        self._canvas._pen.setColor(QtGui.QColor(*color))

    def _on_width_changed(self, width: int):
        self._canvas._pen.setWidth(width)

    def _on_mode_changed(self, mode: DrawMode):
        self._canvas._set_mode(mode)

    def _set_size(self):
        width = self._width_spin.value()
        height = self._height_spin.value()
        self._canvas.set_size(width, height)
        self._size_label.setText(f"{width} px x {height} px")


def _tool_btn(
    icon_name: str, tooltip: str, callback=None, checkable: bool = False
) -> QtW.QToolButton:
    btn = QtW.QToolButton()
    btn.setIcon(QIconifyIcon(icon_name))
    btn.setCheckable(checkable)
    btn.setToolTip(tooltip)
    if callback:
        btn.clicked.connect(callback)
    return btn


class QDrawModeButtons(QtW.QWidget):
    modeChanged = QtCore.Signal(DrawMode)

    def __init__(self):
        super().__init__()
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(0, 0, 0, 0)
        _layout.setSpacing(1)
        _layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._draw_button = _tool_btn(
            icon_name="material-symbols:brush",
            tooltip="Draw mode",
            callback=lambda: self._set_mode(DrawMode.DRAW),
            checkable=True,
        )
        self._erase_button = _tool_btn(
            icon_name="material-symbols:ink-eraser-outline",
            tooltip="Erase mode",
            callback=lambda: self._set_mode(DrawMode.ERASE),
            checkable=True,
        )
        self._pick_button = _tool_btn(
            icon_name="mdi:pipette",
            tooltip="Pick color mode",
            callback=lambda: self._set_mode(DrawMode.PICK),
            checkable=True,
        )
        self._fill_button = _tool_btn(
            icon_name="material-symbols:colors",
            tooltip="Fill mode",
            callback=lambda: self._set_mode(DrawMode.FILL),
            checkable=True,
        )

        _layout.addWidget(self._draw_button)
        _layout.addWidget(self._erase_button)
        _layout.addWidget(self._pick_button)
        _layout.addWidget(self._fill_button)

    def _set_mode(self, mode: DrawMode):
        self._draw_button.setChecked(mode is DrawMode.DRAW)
        self._erase_button.setChecked(mode is DrawMode.ERASE)
        self._pick_button.setChecked(mode is DrawMode.PICK)
        self._fill_button.setChecked(mode is DrawMode.FILL)
        self.modeChanged.emit(mode)
