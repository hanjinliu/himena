from __future__ import annotations
from typing import TYPE_CHECKING
import weakref
from app_model.types import KeyCode

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class KeySet:
    def __init__(self, ui: MainWindow):
        self._ui_ref = weakref.ref(ui)

    def contains(self, key: int | str | KeyCode) -> bool:
        """Check if the given key is currently pressed."""
        if isinstance(key, str):
            _key = KeyCode.from_string(key)
        elif isinstance(key, KeyCode):
            _key = key
        elif isinstance(key, int):
            _key = KeyCode(key)
        else:
            raise TypeError(f"key must be int, str, or KeyCode, not {type(key)}")
        ui = self._ui_ref()
        if ui is None:
            return False

        return _key.value in ui._backend_main_window._keys_as_set()

    __contains__ = contains

    def __repr__(self) -> str:
        ui = self._ui_ref()
        if ui is None:
            return "KeySet(<deleted>)"
        keys = ui._backend_main_window._keys_as_set()
        strs = " ".join(KeyCode(k).os_symbol() for k in keys)
        return f"KeySet({strs})"
