from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator
import uuid
import weakref
from himena.utils.misc import is_subtype
from himena.workflow._base import WorkflowStep
from himena.workflow._reader import ReaderMethod, LocalReaderMethod
from himena.workflow._command import CommandExecution

if TYPE_CHECKING:
    from typing import Self
    from himena.widgets import MainWindow


@dataclass
class ActionMatcher(ABC):
    """Class that determine if a workflow step satisfies a specific condition."""

    model_type: str
    """The model type of the output window."""

    @abstractmethod
    def match(self, model_type: str, step: WorkflowStep) -> bool:
        """Check if the action matcher matches the given workflow step."""


@dataclass
class ReaderMatcher(ActionMatcher):
    """Matches workflow steps that are data loaders."""

    plugins: list[str] = field(default_factory=list)

    def match(self, model_type: str, step: WorkflowStep) -> bool:
        if is_subtype(model_type, self.model_type) and isinstance(step, ReaderMethod):
            return (
                step.plugin is None
                or len(self.plugins) == 0
                or step.plugin in self.plugins
            )
        return False


@dataclass
class CommandMatcher(ActionMatcher):
    """Matches workflow steps by the command ID."""

    command_id: str

    def match(self, model_type: str, step: WorkflowStep) -> bool:
        if (
            is_subtype(model_type, self.model_type)
            and isinstance(step, CommandExecution)
            and step.command_id == self.command_id
        ):
            # TODO: match parameters and contexts
            return True
        return False


@dataclass
class CommandSuggestion:
    """Next action that is a command execution."""

    command_id: str
    """The ID of the command to execute."""
    window_id: Callable[[WorkflowStep], uuid.UUID] | None = None
    """The model context to use for the command execution, if any."""
    defaults: dict[str, Callable[[WorkflowStep], Any]] = field(default_factory=dict)
    """Default parameter overrides."""
    user_context: Callable[[MainWindow, WorkflowStep], dict[str, Any]] | None = None

    def execute(self, main_window: MainWindow, step: WorkflowStep) -> None:
        """Execute the suggestion in the given main window."""
        params = {}
        for key, factory in self.defaults.items():
            value = factory(step)
            params[key] = value
        if self.window_id is not None:
            window_context = main_window.window_for_id(self.window_id(step))
        else:
            window_context = None
        ctx = None
        if self.user_context is not None:
            ctx = self.user_context(main_window, step)
        main_window.exec_action(
            self.command_id,
            window_context=window_context,
            user_context=ctx,
            with_defaults=params,
        )

    def get_title(self, main_window: MainWindow) -> str:
        """Get the title of the command suggestion."""
        if cmd := main_window.model_app.registered_actions.get(self.command_id, None):
            return cmd.title
        return "Unknown Command"

    def get_tooltip(self, main_window: MainWindow) -> str:
        """Get the tooltip for the command suggestion."""
        if cmd := main_window.model_app.registered_actions.get(self.command_id, None):
            return cmd.tooltip
        return "No tooltip available for this command."

    def make_executor(
        self, main_window: MainWindow, step: WorkflowStep
    ) -> SuggestionExecutor:
        """Create an executor for the suggestion."""
        return SuggestionExecutor(self, main_window, step)


class SuggestionExecutor:
    def __init__(
        self, suggestion: CommandSuggestion, main_window: MainWindow, step: WorkflowStep
    ):
        self._suggestion = suggestion
        self._main_window_ref = weakref.ref(main_window)
        self._step = step

    def __call__(self) -> None:
        return self._suggestion.execute(self._get_main_window(), self._step)

    def _get_main_window(self) -> MainWindow | None:
        if ui := self._main_window_ref():
            return ui
        raise RuntimeError("Main window has been deleted.")

    @property
    def command_id(self) -> str:
        """Command ID that will be executed by this suggestion."""
        return self._suggestion.command_id

    def get_user_context(self) -> dict[str, Any] | None:
        """Unwrap and get the user context for this suggestion if any."""
        ui = self._get_main_window()
        if self._suggestion.user_context is not None:
            return self._suggestion.user_context(ui, self._step)


@dataclass
class ActionHint:
    matcher: ActionMatcher
    """The matcher that determines if this action hint is applicable."""
    suggestion: CommandSuggestion
    """The next action to take if this action hint is applicable."""


class ActionHintRegistry:
    """Registry for managing action hints."""

    def __init__(self):
        self._rough_map: dict[str, list[ActionHint]] = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:" + "".join(
            f"\n- {each!r}" for each in self.iter_all()
        )

    def iter_all(self) -> Iterator[ActionHint]:
        """Iterate over all action hints in the registry."""
        for hints in self._rough_map.values():
            yield from hints

    def add_hint(self, matcher: ActionMatcher, suggestion: CommandSuggestion) -> None:
        """Add a matcher to the registry."""
        ancestor_type = matcher.model_type.split(".")[0]
        if ancestor_type not in self._rough_map:
            self._rough_map[ancestor_type] = []
        self._rough_map[ancestor_type].append(ActionHint(matcher, suggestion))

    def when_command_executed(
        self,
        model_type: str,
        command_id: str,
    ) -> ActionMatcherInterface:
        """Create an interface for adding command suggestions.

        Examples
        --------
        >>> (
        ...     reg.when_command_executed("table", "sort-table")
        ...        .add_command_suggestion("scatter-plot")
        ...        .add_command_suggestion("line-plot")
        ... )
        """
        matcher = CommandMatcher(model_type=model_type, command_id=command_id)
        return ActionMatcherInterface(self, matcher)

    def when_reader_used(
        self,
        model_type: str,
        plugins: list[str] | None = None,
    ) -> ActionMatcherInterface:
        """Create an interface for adding reader suggestions.

        Examples
        --------
        >>> (
        ...     reg.when_reader_used("table")
        ...        .add_command_suggestion("load-csv")
        ... )
        """
        matcher = ReaderMatcher(model_type=model_type, plugins=plugins or [])
        return ActionMatcherInterface(self, matcher)

    def iter_suggestion(
        self, model_type: str, step: WorkflowStep
    ) -> Iterator[CommandSuggestion]:
        """Get a list of matchers that match the given model type and step."""
        for ancestor_type, hints in self._rough_map.items():
            if is_subtype(model_type, ancestor_type):
                for hint in hints:
                    if hint.matcher.match(model_type, step):
                        yield hint.suggestion

    def iter_executors_for_file(
        self,
        ui: MainWindow,
        path: str | Path,
        plugin: str | None = None,
    ) -> Iterator[SuggestionExecutor]:
        """Iterate over all the executors available for the given file path."""
        from himena._providers import ReaderStore

        ins = ReaderStore.instance()
        reader_plugin = ins.pick(path, plugin=plugin)
        model_type = reader_plugin.match_model_type(path)
        if plugin := reader_plugin.plugin_str:
            plugins = [plugin]
        else:
            plugins = []
        interf = self.when_reader_used(model_type, plugins=plugins)
        reg = interf._registry
        meth = LocalReaderMethod(output_model_type=model_type, path=path)
        for suggest in reg.iter_suggestion(model_type, meth):
            yield suggest.make_executor(ui, meth)


class ActionMatcherInterface:
    def __init__(self, reg: ActionHintRegistry, matcher: ActionMatcher):
        self._registry = reg
        self._matcher = matcher

    def add_command_suggestion(
        self,
        command_id: str,
        window_id: Callable[[WorkflowStep], uuid.UUID] | None = None,
        defaults: dict[str, Callable[[WorkflowStep], Any]] | None = None,
        user_context: Callable[[MainWindow, WorkflowStep], dict[str, Any]]
        | None = None,
    ) -> Self:
        """Add a suggestion to the registry.

        Parameters
        ----------
        command_id : str
            The command ID that will be suggested for the action.
        window_id : Callable[[WorkflowStep], uuid.UUID], default None
            A function that returns the window ID to use as context for the command.
            Returned value will be passed to the `window_context` parameter of the
            `ui.exec_action` method.
        defaults : dict[str, Callable[[WorkflowStep], Any]], default None
            A dictionary of parameter names to functions that generate default values.
            Returned values will be passed to the `with_defaults` parameter of the
            `ui.exec_action` method.
        """
        suggestion = CommandSuggestion(
            command_id=command_id,
            window_id=window_id,
            defaults=defaults or {},
            user_context=user_context,
        )
        self._registry.add_hint(self._matcher, suggestion)
        return self

    def iter_executables(
        self,
        ui: MainWindow,
        path: str | Path,
    ) -> Iterator[SuggestionExecutor]:
        reg = self._registry
        mtype = self._matcher.model_type
        meth = LocalReaderMethod(output_model_type=mtype, path=path)
        for suggest in reg.iter_suggestion(mtype, meth):
            yield suggest.make_executor(ui, meth)
