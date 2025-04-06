from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar
from himena.utils.enum import StrEnum
from himena.types import Size, WindowRect, Margins

if TYPE_CHECKING:
    from himena.widgets import SubWindow

_W = TypeVar("_W", bound=Any)


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


def prevent_window_overlap(
    win: SubWindow[_W],
    win_to_move: SubWindow[_W],
    area_size: tuple[int, int],
) -> WindowRect:
    """Find a comfortable position to move the window.

    Parameters
    ----------
    win : SubWindow
        The window that should not be overlapped by the other window.
    win_to_move : SubWindow
        The window that should be moved to prevent overlap with `win`.
    area_size : tuple[int, int]
        The size of the area in which the window should be moved.
    """
    offset = 8
    asize = Size(*area_size)
    margins = Margins.from_rects(win.rect, WindowRect(0, 0, *asize))
    rect_orig = win_to_move.rect
    size_orig = rect_orig.size()
    if size_orig.width < margins.right:
        out = rect_orig.move_top_left(
            win.rect.right + offset,
            min(win.rect.top, max(asize.height - size_orig.height - offset, 0)),
        )
    elif size_orig.width < margins.left:
        out = rect_orig.move_top_right(
            win.rect.left - offset,
            min(win.rect.top, max(asize.height - size_orig.height - offset, 0)),
        )
    elif size_orig.height < margins.bottom:
        out = rect_orig.move_top_left(
            min(win.rect.left, max(asize.width - size_orig.width - offset, 0)),
            win.rect.bottom + offset,
        )
    elif size_orig.height < margins.top:
        out = rect_orig.move_bottom_left(
            min(win.rect.left, max(asize.width - size_orig.width - offset, 0)),
            win.rect.top - offset,
        )
    elif margins.bottom < margins.right:
        out = rect_orig.move_top_left(win.rect.right + offset, win.rect.top)
    else:
        out = rect_orig.move_bottom_left(win.rect.left, win.rect.bottom + offset)
    return out
