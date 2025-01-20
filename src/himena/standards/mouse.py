from __future__ import annotations

from typing import Generic, TypeVar

_E = TypeVar("_E")


class MouseEventHandler(Generic[_E]):
    def pressed(self, event: _E):
        """Callback for when the mouse is pressed."""

    def moved(self, event: _E):
        """Callback for when the mouse is moved."""

    def released(self, event: _E):
        """Callback for when the mouse is released."""

    def double_clicked(self, event: _E):
        """Callback for when the mouse is double clicked."""
