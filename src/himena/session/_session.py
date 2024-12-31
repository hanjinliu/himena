from pathlib import Path
from logging import getLogger
from typing import Any, TypeVar, TYPE_CHECKING
from pydantic_compat import BaseModel, Field
import yaml

from himena._descriptors import SaveToPath, dict_to_workflow, workflow_to_dict
from himena.types import WindowState, WindowRect
from himena import anchor, _providers
from himena.widgets._widget_list import TabArea

if TYPE_CHECKING:
    from himena.widgets import SubWindow, MainWindow

_W = TypeVar("_W")  # backend widget type
_LOGGER = getLogger(__name__)


class WindowRectModel(BaseModel):
    """A model version of a window rectangle."""

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


class ReadFromModel(BaseModel):
    """A model that describes how to read a model."""

    path: Path | list[Path] = Field(...)
    plugin: str | None = Field(default=None)


class WindowDescription(BaseModel):
    """A model that describes a window state."""

    title: str
    workflow: dict[str, Any]
    rect: WindowRectModel
    state: WindowState = Field(default=WindowState.NORMAL)
    anchor: dict[str, Any] = Field(default_factory=lambda: {"type": "no-anchor"})
    identifier: int = Field(default=0)
    read_from: ReadFromModel = Field(...)

    @classmethod
    def from_gui(cls, window: "SubWindow") -> "WindowDescription":
        """Construct a WindowDescription from a SubWindow instance."""
        read_from = window._determine_read_from()
        if read_from is None:
            raise ValueError("Cannot determine where to read the model from.")
        return WindowDescription(
            title=window.title,
            workflow=workflow_to_dict(window._widget_data_model_workflow),
            rect=WindowRectModel.from_tuple(window.rect),
            state=window.state,
            anchor=anchor.anchor_to_dict(window.anchor),
            identifier=window._identifier,
            read_from=ReadFromModel(path=read_from[0], plugin=read_from[1]),
        )


class TabSession(BaseModel):
    """A session of a tab."""

    name: str = Field(default="")
    windows: list[WindowDescription] = Field(default_factory=list)
    current_index: int | None = Field(default=None)

    @classmethod
    def from_gui(cls, tab: TabArea) -> "TabSession":
        return TabSession(
            name=tab.name,
            current_index=tab.current_index,
            windows=[WindowDescription.from_gui(window) for window in tab],
        )

    def update_gui(self, main: "MainWindow[_W]") -> None:
        """Update the GUI state based on the session."""
        area = main.add_tab(self.name)
        cur_index = self.current_index
        store = _providers.ReaderProviderStore().instance()
        for window_session in self.windows:
            try:
                model = store.run(
                    path=window_session.read_from.path,
                    plugin=window_session.read_from.plugin,
                )
            except Exception as e:
                cur_index -= 1
                _LOGGER.warning(
                    "Could not load a window %r: %s", window_session.title, e
                )
                continue
            model.workflow = dict_to_workflow(window_session.workflow)
            window = area.add_data_model(model)
            window.title = window_session.title
            window.rect = window_session.rect.to_tuple()
            window.state = window_session.state
            window.anchor = anchor.dict_to_anchor(window_session.anchor)
            window._save_behavior = SaveToPath(
                path=window_session.read_from.path,
                plugin=window_session.read_from.plugin,
            )
        if 0 <= cur_index < len(area):
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

    def update_gui(self, main: "MainWindow[_W]") -> None:
        """Update the GUI state based on the session."""
        cur_index = self.current_index
        for tab_session in self.tabs:
            tab_session.update_gui(main)
        main.tabs.current_index = self.current_index + cur_index
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
