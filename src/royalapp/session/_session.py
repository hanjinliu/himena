from typing import Any, TypeVar
from pydantic_compat import BaseModel, Field

from royalapp._descriptors import MethodDescriptor
from royalapp.types import WindowState, WindowRect
from royalapp.widgets import SubWindow, MainWindow
from royalapp import anchor
from royalapp.widgets._tab_list import TabArea

_W = TypeVar("_W")  # backend widget type


class WindowDescription(BaseModel):
    title: str = Field(...)
    method: MethodDescriptor
    rect: WindowRect = Field(...)
    state: WindowState = Field(...)
    anchor: dict[str, Any] = Field(default_factory=lambda: {"type": "no-anchor"})
    identifier: int = Field(default=0)

    @classmethod
    def from_gui(cls, window: SubWindow) -> "WindowDescription":
        return WindowDescription(
            title=window.title,
            method=window._widget_data_model_method,
            rect=window.rect,
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
            windows=[WindowDescription.from_gui(window) for window in tab],
            current_index=tab.current_index,
        )


class AppSession(BaseModel):
    """A session of the entire application."""

    tabs: list[TabSession] = Field(default_factory=list)
    current_index: int = Field(default=0)

    @classmethod
    def from_gui(cls, main: MainWindow) -> "AppSession":
        return AppSession(
            tabs=[TabSession.from_gui(tab) for tab in main.tabs],
            current_index=main.tabs.current_index,
        )

    def to_gui(self, main: MainWindow[_W]) -> None:
        main.tabs.clear()  # initialize
        for tab_session in self.tabs:
            area = main.add_tab(tab_session.name)
            for window_session in tab_session.windows:
                model = window_session.method.get_model(main.model_app)
                window = area.add_data_model(model)
                window.rect = window_session.rect
                window.state = window_session.state
                window.anchor = anchor.dict_to_anchor(window_session.anchor)
            area.current_index = tab_session.current_index
        main.tabs.current_index = self.current_index
        return None
