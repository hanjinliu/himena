from __future__ import annotations

from himena._enum import StrEnum
from himena.types import Size, WindowRect


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

    def resize_widget(
        self,
        widget_rect: WindowRect,
        mouse_pos: tuple[int, int],
        min_size: Size,
        max_size: Size,
    ) -> WindowRect | None:
        w_adj = _SizeAdjuster(min_size.width, max_size.width)
        h_adj = _SizeAdjuster(min_size.height, max_size.height)
        mx, my = mouse_pos
        if self is ResizeState.TOP_LEFT:
            out = WindowRect(
                widget_rect.left + mx,
                widget_rect.top + my,
                w_adj(widget_rect.width - mx),
                h_adj(widget_rect.height - my),
            )
        elif self is ResizeState.BOTTOM_LEFT:
            out = WindowRect(
                widget_rect.left + mx,
                widget_rect.top,
                w_adj(widget_rect.width - mx),
                h_adj(my),
            )
        elif self is ResizeState.TOP_RIGHT:
            out = WindowRect(
                widget_rect.left,
                widget_rect.top + my,
                w_adj(mx),
                h_adj(widget_rect.height - my),
            )
        elif self is ResizeState.BOTTOM_RIGHT:
            out = WindowRect(
                widget_rect.left,
                widget_rect.top,
                w_adj(mx),
                h_adj(my),
            )
        elif self is ResizeState.TOP:
            out = WindowRect(
                widget_rect.left,
                widget_rect.top + my,
                w_adj(widget_rect.width),
                h_adj(widget_rect.height - my),
            )
        elif self is ResizeState.BOTTOM:
            out = WindowRect(
                widget_rect.left,
                widget_rect.top,
                w_adj(widget_rect.width),
                h_adj(my),
            )
        elif self is ResizeState.LEFT:
            out = WindowRect(
                widget_rect.left + mx,
                widget_rect.top,
                w_adj(widget_rect.width - mx),
                h_adj(widget_rect.height),
            )
        elif self is ResizeState.RIGHT:
            out = WindowRect(
                widget_rect.left,
                widget_rect.top,
                w_adj(mx),
                h_adj(widget_rect.height),
            )
        else:
            out = None
        return out


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
