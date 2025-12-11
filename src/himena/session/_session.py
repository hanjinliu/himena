from contextlib import suppress
import importlib
from pathlib import Path
from typing import Any, Mapping, TypeVar, TYPE_CHECKING
import uuid
import warnings
from pydantic import BaseModel, Field

from himena._descriptors import NoNeedToSave, SaveToPath
from himena._utils import get_widget_class_id
from himena.layout import construct_layout
from himena.types import WindowState, WindowRect, WidgetDataModel
from himena.utils.misc import is_subtype
from himena import anchor
from himena._providers import ReaderStore
from himena.widgets._wrapper import ParametricWindow
from himena.standards import read_metadata
from himena.workflow import Workflow, compute, WorkflowStepType, LocalReaderMethod

if TYPE_CHECKING:
    from himena.widgets import SubWindow, TabArea, MainWindow

_W = TypeVar("_W")  # widget interface


class WindowDescription(BaseModel):
    """A model that describes a window state."""

    title: str
    rect: WindowRect
    state: WindowState = Field(default=WindowState.NORMAL)
    anchor: dict[str, Any] = Field(default_factory=lambda: {"type": "no-anchor"})
    is_editable: bool = Field(default=True)
    id: uuid.UUID
    short_workflow: WorkflowStepType | None = Field(default=None)
    workflow: Workflow
    model_type: str
    widget_plugin_id: str | None = Field(default=None)
    children: list[uuid.UUID] = Field(default_factory=list)

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
            )
        model = window.to_model()
        return WindowDescription(
            title=window.title,
            rect=window.rect,
            state=window.state,
            anchor=anchor.anchor_to_dict(window.anchor),
            is_editable=window.is_editable,
            id=window._identifier,
            short_workflow=short_workflow,
            workflow=model.workflow,
            model_type=model.type,
            widget_plugin_id=get_widget_class_id(type(window.widget)),
            children=[child._identifier for child in window._child_windows],
        )

    def process_model(self, area: "TabArea[_W]", model: "WidgetDataModel"):
        """Add model to the tab area and update the window properties."""
        model.workflow = self.workflow
        model.save_behavior_override = NoNeedToSave()
        if widget_plugin_id := self.widget_plugin_id:
            try:
                window = area.add_data_model(model.with_open_plugin(widget_plugin_id))
            except Exception as e:
                window = area.add_data_model(model)
                warnings.warn(
                    "Could not open the file with the intended widget plugin "
                    f"{widget_plugin_id} because of the following error: {e}",
                    RuntimeWarning,
                    stacklevel=2,
                )
        else:
            window = area.add_data_model(model)
        window.title = self.title
        window.rect = self.rect
        window.state = self.state
        window.anchor = anchor.dict_to_anchor(self.anchor)
        with suppress(AttributeError):
            window.is_editable = self.is_editable
        if isinstance(meth := self.short_workflow, LocalReaderMethod):
            window._save_behavior = SaveToPath(path=meth.path, plugin=meth.plugin)
        window._identifier = self.id
        return window

    def prep_workflow(
        self, workflow_override: Mapping[uuid.UUID, Workflow]
    ) -> Workflow:
        """Prepare the most efficient workflow to get the window."""
        if wf := workflow_override.get(self.id):
            pass
        else:
            if self.short_workflow is None:
                wf = self.workflow
            else:
                wf = Workflow(steps=[self.short_workflow])
        if len(wf) == 1 and isinstance(meth := wf[0], LocalReaderMethod):
            # look for the best reader according to _win_sessions.model_type
            if meth.plugin is None:
                meth.plugin = _pick_best_reader_plugin(meth, self.model_type)
        return wf


class TabSession(BaseModel):
    """A session of a tab."""

    name: str = Field(default="")
    windows: list[WindowDescription] = Field(default_factory=list)
    current_index: int | None = Field(default=None)
    layouts: list[dict] = Field(default_factory=list)

    @classmethod
    def from_gui(
        cls,
        tab: "TabArea[_W]",
        *,
        allow_calculate: bool = False,
    ) -> "TabSession":
        layouts: list[dict] = []
        for ly in tab.layouts:
            if ly is tab._minimized_window_stack_layout:
                continue  # this layout does not need to be saved
            layouts.append(ly._serialize_layout())
        return TabSession(
            name=tab.name,
            windows=[
                WindowDescription.from_gui(window, allow_calculate=allow_calculate)
                for window in tab
                if not isinstance(window, ParametricWindow)
            ],
            current_index=tab.current_index,
            layouts=layouts,
        )

    def update_gui(
        self,
        main: "MainWindow[_W]",
        *,
        workflow_override: Mapping[str, Workflow] = {},
        dirpath: Path,
    ) -> None:
        """Update the GUI state based on the session."""
        _win_sessions: list[tuple[int, WindowDescription]] = []
        _pending_workflows: list[Workflow] = []
        area = main.add_tab(self.name)
        cur_index = self.current_index
        for i_win, window_session in enumerate(self.windows):
            _win_sessions.append((i_win, window_session))
            wf = window_session.prep_workflow(workflow_override)
            _pending_workflows.append(wf)

        models = compute(_pending_workflows)
        _failed_sessions: list[tuple[WindowDescription, Exception]] = []
        _id_to_win: dict[uuid.UUID, "SubWindow"] = {}
        for (i_win_sess, _win_sess), model_or_exc in zip(_win_sessions, models):
            if isinstance(model_or_exc, Exception):
                _failed_sessions.append((_win_sess, model_or_exc))
                continue
            # look for the metadata
            meta_path = dirpath / f"{i_win_sess}_{_win_sess.title}.himena-meta"
            if meta_path.exists():
                try:
                    model_or_exc.metadata = read_metadata(meta_path)
                except Exception as e:
                    warnings.warn(
                        f"Failed to read metadata from {meta_path}: {e}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
            _win = _win_sess.process_model(self, model_or_exc)
            _id_to_win[_win_sess.id] = _win

        if 0 <= cur_index < len(area):
            area.current_index = cur_index
        _raise_failed(_failed_sessions)
        _update_layout(area, self.layouts, main)
        for _win_sess in self.windows:
            for child_id in _win_sess.children:
                _id_to_win[_win_sess.id]._child_windows.add(_id_to_win[child_id])


def _update_layout(tab: "TabArea[_W]", layouts: list[dict], main: "MainWindow[_W]"):
    for ly in layouts:
        _layout_obj = construct_layout(ly, main)
        tab._add_layout_impl(_layout_obj)


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
    rect: WindowRect = Field(default=WindowRect(200, 200, 800, 600))

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
            rect=main.rect,
        )

    def update_gui(
        self,
        main: "MainWindow[_W]",
        *,
        workflow_override: Mapping[str, Workflow] = {},
        dirpath: Path,
    ) -> None:
        """Update the GUI state based on the session."""
        cur_index = self.current_index
        _tab_sessions: list[tuple[int, TabSession]] = []
        _win_sessions: list[tuple[int, WindowDescription]] = []
        _target_areas: list[tuple[int, TabArea]] = []
        _pending_workflows: list[Workflow] = []
        for i_tab, tab_session in enumerate(self.tabs):
            _tab_sessions.append((i_tab, tab_session))
            _new_tab = main.add_tab(tab_session.name)
            for i_win, window_session in enumerate(tab_session.windows):
                _win_sessions.append((i_win, window_session))
                wf = window_session.prep_workflow(workflow_override)
                _pending_workflows.append(wf)
                _target_areas.append((i_tab, _new_tab))

        # read all the metadata
        all_metadata = []
        for (i_win, _win_sess), (i_tab, _tab_area) in zip(_win_sessions, _target_areas):
            # look for the metadata
            meta = None
            meta_path = (
                dirpath
                / f"{i_tab}_{_tab_area.title}"
                / f"{i_win}_{_win_sess.title}.himena-meta"
            )
            if meta_path.exists():
                try:
                    meta = read_metadata(meta_path)
                except Exception as e:
                    warnings.warn(
                        f"Failed to read metadata from {meta_path}: {e}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
            all_metadata.append(meta)
        models = compute(_pending_workflows, all_metadata)
        _failed_sessions: list[tuple[WindowDescription, Exception]] = []
        _id_to_win: dict[uuid.UUID, "SubWindow"] = {}
        for (i_win, _win_sess), (i_tab, _tab_area), model_or_exc in zip(
            _win_sessions, _target_areas, models
        ):
            if isinstance(model_or_exc, Exception):
                _failed_sessions.append((_win_sess, model_or_exc))
                continue
            _id_to_win[_win_sess.id] = _win_sess.process_model(_tab_area, model_or_exc)

        # Update current active window for each tab
        for (_, tab_session), (_, area) in zip(_tab_sessions, _target_areas):
            cur_tab_index = tab_session.current_index
            if cur_tab_index is not None and 0 <= cur_tab_index < len(area):
                area.current_index = cur_tab_index
        main.tabs.current_index = self.current_index + cur_index
        _raise_failed(_failed_sessions)
        main.rect = self.rect
        for tab_session in self.tabs:
            _update_layout(main.tabs[tab_session.name], tab_session.layouts, main)

        # connect window children to their parents
        for _, _win_sess in _win_sessions:
            for child_id in _win_sess.children:
                _id_to_win[_win_sess.id]._child_windows.add(_id_to_win[child_id])


def _raise_failed(failed: list[tuple[WindowDescription, Exception]]) -> None:
    if len(failed) > 0:
        msg = "Could not load the following windows:\n"
        list_of_failed = "\n".join(
            f"- {win.title} ({type(exc).__name__}: {exc})" for win, exc in failed
        )
        raise ValueError(msg + list_of_failed) from failed[-1][1]


def _pick_best_reader_plugin(meth: LocalReaderMethod, expected_type: str) -> str | None:
    ins = ReaderStore().instance()
    suboptimals: list[int, str] = []
    for model_type, reader in ins.iter_readers(meth.path, min_priority=-float("inf")):
        if model_type is None:
            continue
        if model_type == expected_type:
            return reader.plugin.to_str()
        elif is_subtype(model_type, expected_type):
            if reader.plugin is None:
                continue
            score = len(model_type)
            suboptimals.append((score, reader.plugin.to_str()))
    if len(suboptimals) == 0:
        return None
    return max(suboptimals, key=lambda x: x[0])[1]
