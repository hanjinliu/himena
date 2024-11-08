from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy import QtCore
from qtpy.QtCore import Qt
from royalapp.consts import StrEnum


class ResizeState(StrEnum):
    """The state of the resize operation of the window."""

    NONE = "none"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"

    @staticmethod
    def from_bools(
        is_left: bool, is_right: bool, is_top: bool, is_bottom: bool
    ) -> ResizeState:
        """Get the resize state from the edge booleans."""
        return RESIZE_STATE_MAP.get(
            (is_left, is_right, is_top, is_bottom), ResizeState.NONE
        )

    def to_cursor_shape(self) -> Qt.CursorShape:
        """Get the cursor shape for the resize state."""
        return CURSOR_SHAPE_MAP[self]

    def resize_widget(
        self,
        widget: QtW.QWidget,
        mouse_pos: QtCore.QPoint,
        min_size: QtCore.QSize,
        max_size: QtCore.QSize,
    ) -> bool:
        w_adj = _SizeAdjuster(min_size.width(), max_size.width())
        h_adj = _SizeAdjuster(min_size.height(), max_size.height())
        if self is ResizeState.TOP_LEFT:
            widget.setGeometry(
                widget.x() + mouse_pos.x(),
                widget.y() + mouse_pos.y(),
                w_adj(widget.width() - mouse_pos.x()),
                h_adj(widget.height() - mouse_pos.y()),
            )
        elif self is ResizeState.BOTTOM_LEFT:
            widget.setGeometry(
                widget.x() + mouse_pos.x(),
                widget.y(),
                w_adj(widget.width() - mouse_pos.x()),
                h_adj(mouse_pos.y()),
            )
        elif self is ResizeState.TOP_RIGHT:
            widget.setGeometry(
                widget.x(),
                widget.y() + mouse_pos.y(),
                w_adj(mouse_pos.x()),
                h_adj(widget.height() - mouse_pos.y()),
            )
        elif self is ResizeState.BOTTOM_RIGHT:
            widget.setGeometry(
                widget.x(),
                widget.y(),
                w_adj(mouse_pos.x()),
                h_adj(mouse_pos.y()),
            )
        elif self is ResizeState.TOP:
            widget.setGeometry(
                widget.x(),
                widget.y() + mouse_pos.y(),
                w_adj(widget.width()),
                h_adj(widget.height() - mouse_pos.y()),
            )
        elif self is ResizeState.BOTTOM:
            widget.setGeometry(
                widget.x(),
                widget.y(),
                w_adj(widget.width()),
                h_adj(mouse_pos.y()),
            )
        elif self is ResizeState.LEFT:
            widget.setGeometry(
                widget.x() + mouse_pos.x(),
                widget.y(),
                w_adj(widget.width() - mouse_pos.x()),
                h_adj(widget.height()),
            )
        elif self is ResizeState.RIGHT:
            widget.setGeometry(
                widget.x(),
                widget.y(),
                w_adj(mouse_pos.x()),
                h_adj(widget.height()),
            )
        else:
            return False
        return True


class _SizeAdjuster:
    def __init__(self, min_x: int, max_x: int):
        self.min_x = min_x
        self.max_x = max_x

    def __call__(self, x: int) -> int:
        return min(max(x, self.min_x), self.max_x)


# is_left_edge, is_right_edge, is_top_edge, is_bottom_edge
RESIZE_STATE_MAP = {
    (True, False, True, False): ResizeState.TOP_LEFT,
    (False, True, True, False): ResizeState.TOP_RIGHT,
    (True, False, False, True): ResizeState.BOTTOM_LEFT,
    (False, True, False, True): ResizeState.BOTTOM_RIGHT,
    (True, False, False, False): ResizeState.LEFT,
    (False, True, False, False): ResizeState.RIGHT,
    (False, False, True, False): ResizeState.TOP,
    (False, False, False, True): ResizeState.BOTTOM,
    (False, False, False, False): ResizeState.NONE,
}

CURSOR_SHAPE_MAP = {
    ResizeState.TOP: Qt.CursorShape.SizeVerCursor,
    ResizeState.BOTTOM: Qt.CursorShape.SizeVerCursor,
    ResizeState.LEFT: Qt.CursorShape.SizeHorCursor,
    ResizeState.RIGHT: Qt.CursorShape.SizeHorCursor,
    ResizeState.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    ResizeState.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    ResizeState.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    ResizeState.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    ResizeState.NONE: Qt.CursorShape.ArrowCursor,
}
