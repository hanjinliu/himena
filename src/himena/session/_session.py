from contextlib import suppress
import importlib
from pathlib import Path
from typing import Any, TypeVar, TYPE_CHECKING
import uuid
from pydantic_compat import BaseModel, Field
import yaml

from himena._descriptors import SaveToPath
from himena.types import WindowState, WindowRect, WidgetDataModel
from himena import anchor
from himena.workflow import Workflow, compute, WorkflowStepType, LocalReaderMethod

if TYPE_CHECKING:
    from himena.widgets import SubWindow, TabArea, MainWindow

_W = TypeVar("_W")  # widget interface


class WindowRectModel(BaseModel):
    """A model version of a window rectangle."""

    left: int
    top: int
    width: int
    height: int

    @classmethod
    def from_tuple(cls, rect: WindowRect) -> "WindowRectModel":
        left, top, width, height = rect
        return WindowRectModel(left=left, top=top, width=width, height=height)

    def to_tuple(self) -> WindowRect:
        return WindowRect(self.left, self.top, self.width, self.height)


class WindowDescription(BaseModel):
    """A model that describes a window state."""

    title: str
    rect: WindowRectModel
    state: WindowState = Field(default=WindowState.NORMAL)
    anchor: dict[str, Any] = Field(default_factory=lambda: {"type": "no-anchor"})
    is_editable: bool = Field(default=True)
    id: uuid.UUID
    short_workflow: WorkflowStepType | None
    workflow: Workflow

    @classmethod
    def from_gui(
        cls,
        window: "SubWindow",
        *,
        allow_calculate: bool = False,
    ) -> "WindowDescription":
        """Construct a WindowDescription from a SubWindow instance."""
        read_from = window._determine_read_from()
        if read_from is None:
            if allow_calculate:
                short_workflow = None
            else:
                raise ValueError("Cannot determine where to read the model from.")
        else:
            short_workflow = LocalReaderMethod(
                path=read_from[0],
                plugin=read_from[1],
                output_model_type=window.model_type(),
            )
        return WindowDescription(
            title=window.title,
            workflow=window.to_model().workflow,
            rect=WindowRectModel.from_tuple(window.rect),
            state=window.state,
            anchor=anchor.anchor_to_dict(window.anchor),
            is_editable=window.is_editable,
            id=window._identifier,
            short_workflow=short_workflow,
        )

    def process_model(self, area: "TabArea[_W]", model: "WidgetDataModel"):
        """Add model to the tab area and update the window properties."""
        model.workflow = self.workflow
        window = area.add_data_model(model)
        window.title = self.title
        window.rect = self.rect.to_tuple()
        window.state = self.state
        window.anchor = anchor.dict_to_anchor(self.anchor)
        with suppress(AttributeError):
            window.is_editable = self.is_editable
        if isinstance(meth := self.short_workflow, LocalReaderMethod):
            window._save_behavior = SaveToPath(path=meth.path, plugin=meth.plugin)
        window._identifier = self.id
        return model

    def prep_workflow(self) -> Workflow:
        """Prepare the most efficient workflow to get the window."""
        if self.short_workflow is None:
            wf = self.workflow
        else:
            wf = Workflow(steps=[self.short_workflow])
        return wf


class TabSession(BaseModel):
    """A session of a tab."""

    name: str = Field(default="")
    windows: list[WindowDescription] = Field(default_factory=list)
    current_index: int | None = Field(default=None)
    # `layout = Field(default_factory=LayoutModel)` in the future

    @classmethod
    def from_gui(
        cls,
        tab: "TabArea[_W]",
        *,
        allow_calculate: bool = False,
    ) -> "TabSession":
        return TabSession(
            name=tab.name,
            current_index=tab.current_index,
            windows=[
                WindowDescription.from_gui(window, allow_calculate=allow_calculate)
                for window in tab
            ],
        )

    def update_gui(self, main: "MainWindow[_W]") -> None:
        """Update the GUI state based on the session."""
        _win_sessions: list[WindowDescription] = []
        _pending_workflows: list[Workflow] = []
        area = main.add_tab(self.name)
        cur_index = self.current_index
        for window_session in self.windows:
            _win_sessions.append(window_session)
            wf = window_session.prep_workflow()
            _pending_workflows.append(wf)

        models = compute(_pending_workflows)
        _failed_sessions: list[tuple[WindowDescription, Exception]] = []
        for _win_sess, model_or_exc in zip(_win_sessions, models):
            if isinstance(model_or_exc, Exception):
                _failed_sessions.append((_win_sess, model_or_exc))
                continue
            _win_sess.process_model(self, model_or_exc)

        if 0 <= cur_index < len(area):
            area.current_index = cur_index
        _raise_failed(_failed_sessions)
        return None

    def dump_yaml(self, path: str | Path) -> None:
        """Dump the session to a YAML file."""
        js = self.model_dump(mode="json")
        js = {"session": "tab", **js}
        with open(path, "w") as f:
            yaml.dump(js, f, sort_keys=False)
        return None


def _get_version(mod, maybe_file: bool = False) -> str | None:
    if maybe_file and Path(mod).suffix:
        return None
    if isinstance(mod, str):
        mod = importlib.import_module(mod)
    return getattr(mod, "__version__", None)


class AppProfileInfo(BaseModel):
    """A simplified app profile for saving a session."""

    name: str
    plugins: list[str] = Field(default_factory=list)
    theme: str


class AppSession(BaseModel):
    """A session of the entire application."""

    version: str | None = Field(default_factory=lambda: _get_version("himena"))
    profile: AppProfileInfo | None = Field(default=None)
    tabs: list[TabSession] = Field(default_factory=list)
    current_index: int = Field(default=0)

    @classmethod
    def from_gui(
        cls,
        main: "MainWindow[_W]",
        *,
        allow_calculate: bool = False,
    ) -> "AppSession":
        app_prof = main.app_profile
        profile = AppProfileInfo(
            name=app_prof.name,
            plugins=app_prof.plugins,
            theme=app_prof.theme,
        )
        return AppSession(
            profile=profile,
            tabs=[
                TabSession.from_gui(tab, allow_calculate=allow_calculate)
                for tab in main.tabs
            ],
            current_index=main.tabs.current_index,
        )

    def update_gui(
        self,
        main: "MainWindow[_W]",
        *,
        workflow_overload: dict[str, Workflow] = {},
    ) -> None:
        """Update the GUI state based on the session."""
        cur_index = self.current_index
        _tab_sessions: list[TabSession] = []
        _win_sessions: list[WindowDescription] = []
        _target_areas: list[TabArea] = []
        _pending_workflows: list[Workflow] = []
        for tab_session in self.tabs:
            _tab_sessions.append(tab_session)
            _new_tab = main.add_tab(tab_session.name)
            for window_session in tab_session.windows:
                _win_sessions.append(window_session)
                if wf := workflow_overload.get(window_session.id):
                    pass
                else:
                    wf = window_session.prep_workflow()
                _pending_workflows.append(wf)
                _target_areas.append(_new_tab)
        models = compute(_pending_workflows)
        _failed_sessions: list[tuple[WindowDescription, Exception]] = []
        for _win_sess, _tab_area, model_or_exc in zip(
            _win_sessions, _target_areas, models
        ):
            if isinstance(model_or_exc, Exception):
                _failed_sessions.append((_win_sess, model_or_exc))
                continue
            _win_sess.process_model(_tab_area, model_or_exc)

        # Update current active window for each tab
        for tab_session, area in zip(_tab_sessions, _target_areas):
            cur_tab_index = tab_session.current_index
            if cur_tab_index is not None and 0 <= cur_tab_index < len(area):
                area.current_index = cur_tab_index
        main.tabs.current_index = self.current_index + cur_index
        _raise_failed(_failed_sessions)
        return None


def _raise_failed(failed: list[tuple[WindowDescription, Exception]]) -> None:
    if len(failed) > 0:
        msg = "Could not load the following windows:\n"
        list_of_failed = "\n".join(
            f"- {win.title} ({type(exc).__name__}:{exc})" for win, exc in failed
        )
        raise ValueError(msg + list_of_failed) from failed[-1][1]
