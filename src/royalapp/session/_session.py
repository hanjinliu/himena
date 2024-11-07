from pathlib import Path
from logging import getLogger
from typing import Any, TypeVar, TYPE_CHECKING
from pydantic_compat import BaseModel, Field
import yaml

from royalapp._descriptors import dict_to_method, method_to_dict
from royalapp.types import WindowState, WindowRect
from royalapp import anchor
from royalapp.widgets._tab_list import TabArea

if TYPE_CHECKING:
    from royalapp.widgets import SubWindow, MainWindow

_W = TypeVar("_W")  # backend widget type
_LOGGER = getLogger(__name__)


class WindowRectModel(BaseModel):
    left: int = Field(...)
    top: int = Field(...)
    width: int = Field(...)
    height: int = Field(...)

    @classmethod
    def from_tuple(cls, rect: WindowRect) -> "WindowRectModel":
        left, top, width, height = rect
        return WindowRectModel(left=left, top=top, width=width, height=height)

    def to_tuple(self) -> WindowRect:
        return WindowRect(self.left, self.top, self.width, self.height)


class WindowDescription(BaseModel):
    title: str
    method: dict[str, Any]
    rect: WindowRectModel
    state: WindowState = Field(default=WindowState.NORMAL)
    anchor: dict[str, Any] = Field(default_factory=lambda: {"type": "no-anchor"})
    identifier: int = Field(default=0)

    @classmethod
    def from_gui(cls, window: "SubWindow") -> "WindowDescription":
        return WindowDescription(
            title=window.title,
            method=method_to_dict(window._widget_data_model_method),
            rect=WindowRectModel.from_tuple(window.rect),
            state=window.state,
            anchor=anchor.anchor_to_dict(window.anchor),
            identifier=window._identifier,
        )


class TabSession(BaseModel):
    """A session of a tab."""

    name: str = Field(default="")
    windows: list[WindowDescription] = Field(default_factory=list)
    current_index: int = Field(default=0)

    @classmethod
    def from_gui(cls, tab: TabArea) -> "TabSession":
        return TabSession(
            name=tab.name,
            current_index=tab.current_index,
            windows=[WindowDescription.from_gui(window) for window in tab],
        )

    def to_gui(self, main: "MainWindow[_W]") -> None:
        with main._animation_context(enabled=False):
            area = main.add_tab(self.name)
            cur_index = self.current_index
            for window_session in self.windows:
                try:
                    method_desc = dict_to_method(window_session.method)
                    model = method_desc.get_model(main.model_app)
                except Exception:
                    cur_index -= 1
                    continue  # TODO: inform user
                window = area.add_data_model(model)
                window.title = window_session.title
                window.rect = window_session.rect.to_tuple()
                window.state = window_session.state
                window.anchor = anchor.dict_to_anchor(window_session.anchor)
            if cur_index >= 0:
                area.current_index = cur_index
        return None

    def dump_yaml(self, path: str | Path) -> None:
        js = self.model_dump(mode="json")
        js = {"session": "tab", **js}
        with open(path, "w") as f:
            yaml.dump(js, f, sort_keys=False)
        return None


class AppSession(BaseModel):
    """A session of the entire application."""

    tabs: list[TabSession] = Field(default_factory=list)
    current_index: int = Field(default=0)

    @classmethod
    def from_gui(cls, main: "MainWindow[_W]") -> "AppSession":
        return AppSession(
            tabs=[TabSession.from_gui(tab) for tab in main.tabs],
            current_index=main.tabs.current_index,
        )

    def to_gui(self, main: "MainWindow[_W]") -> None:
        with main._animation_context(enabled=False):
            for tab_session in self.tabs:
                area = main.add_tab(tab_session.name)
                cur_index = tab_session.current_index
                for window_session in tab_session.windows:
                    try:
                        method_desc = dict_to_method(window_session.method)
                        model = method_desc.get_model(main.model_app)
                    except Exception:
                        cur_index -= 1
                        continue  # TODO: inform user
                    window = area.add_data_model(model)
                    _LOGGER.info("Got model: %r", model)
                    window.title = window_session.title
                    window.rect = window_session.rect.to_tuple()
                    window.state = window_session.state
                    window.anchor = anchor.dict_to_anchor(window_session.anchor)
                if cur_index >= 0:
                    area.current_index = cur_index
        return None

    def dump_yaml(self, path: str | Path) -> None:
        js = self.model_dump(mode="json")
        js = {"session": "main", **js}
        with open(path, "w") as f:
            yaml.dump(js, f, sort_keys=False)
        return None


def from_yaml(path: str | Path) -> AppSession | TabSession:
    with open(path) as f:
        yml = yaml.load(f, Loader=yaml.Loader)
    if not (isinstance(yml, dict) and "session" in yml):
        raise ValueError("Invalid session file.")
    session_type = yml.pop("session")
    if session_type == "main":
        return AppSession.model_validate(yml)
    elif session_type == "tab":
        return TabSession.model_validate(yml)
    else:
        raise ValueError("Invalid session file.")
