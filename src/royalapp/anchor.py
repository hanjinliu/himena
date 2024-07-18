from __future__ import annotations

from typing import TYPE_CHECKING
from royalapp.types import WindowRect

if TYPE_CHECKING:
    from typing_extensions import Self


class WindowAnchor:
    def apply_anchor(
        self,
        main_window_size: tuple[int, int],
        sub_window_size: tuple[int, int],
    ) -> WindowRect | None:
        return None

    def update_for_window_rect(
        self,
        main_window_size: tuple[int, int],
        window_rect: WindowRect,
    ) -> Self:
        return self


NoAnchor = WindowAnchor()


class TopLeftConstAnchor(WindowAnchor):
    def __init__(self, left: int, top: int):
        self._left = left
        self._top = top

    def apply_anchor(
        self,
        main_window_size: tuple[int, int],
        sub_window_size: tuple[int, int],
    ) -> WindowRect | None:
        w, h = sub_window_size
        return WindowRect.from_numbers(self._left, self._top, w, h)

    def update_for_window_rect(
        self,
        main_window_size: tuple[int, int],
        window_rect: WindowRect,
    ) -> Self:
        return TopLeftConstAnchor(window_rect.left, window_rect.top)


class TopRightConstAnchor(WindowAnchor):
    def __init__(self, right: int, top: int):
        self._right = right
        self._top = top

    def apply_anchor(
        self,
        main_window_size: tuple[int, int],
        sub_window_size: tuple[int, int],
    ) -> WindowRect | None:
        main_w, _ = main_window_size
        w, h = sub_window_size
        return WindowRect.from_numbers(main_w - self._right - w, self._top, w, h)

    def update_for_window_rect(
        self,
        main_window_size: tuple[int, int],
        window_rect: WindowRect,
    ) -> Self:
        w0 = main_window_size[1]
        return TopRightConstAnchor(w0 - window_rect.right, window_rect.top)


class BottomLeftConstAnchor(WindowAnchor):
    def __init__(self, left: int, bottom: int):
        self._left = left
        self._bottom = bottom

    def apply_anchor(
        self,
        main_window_size: tuple[int, int],
        sub_window_size: tuple[int, int],
    ) -> WindowRect | None:
        _, main_h = main_window_size
        w, h = sub_window_size
        return WindowRect.from_numbers(self._left, main_h - self._bottom - h, w, h)

    def update_for_window_rect(
        self,
        main_window_size: tuple[int, int],
        window_rect: WindowRect,
    ) -> Self:
        h0 = main_window_size[1]
        return BottomLeftConstAnchor(window_rect.left, h0 - window_rect.bottom)


class BottomRightConstAnchor(WindowAnchor):
    def __init__(self, right: int, bottom: int):
        self._right = right
        self._bottom = bottom

    def apply_anchor(
        self,
        main_window_size: tuple[int, int],
        sub_window_size: tuple[int, int],
    ) -> WindowRect | None:
        main_w, main_h = main_window_size
        w, h = sub_window_size
        return WindowRect.from_numbers(
            main_w - self._right - w, main_h - self._bottom - h, w, h
        )

    def update_for_window_rect(
        self,
        main_window_size: tuple[int, int],
        window_rect: WindowRect,
    ) -> Self:
        w0, h0 = main_window_size
        return BottomRightConstAnchor(w0 - window_rect.right, h0 - window_rect.bottom)
