from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterator
from himena.workflow._base import WorkflowStep
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
class CommandMatcher(ActionMatcher):
    """Matches workflow steps that are command-line based."""

    command_id: str

    def match(self, model_type: str, step: WorkflowStep) -> bool:
        if (
            model_type == self.model_type
            and isinstance(step, CommandExecution)
            and step.command_id == self.command_id
        ):
            return True
        return False


@dataclass
class Suggestion(ABC):
    @abstractmethod
    def execute(self, main_window: MainWindow) -> None:
        """Execute the suggestion in the given main window."""

    @abstractmethod
    def get_title(self, main_window: MainWindow) -> str:
        """Get the title of the suggestion."""

    @abstractmethod
    def get_tooltip(self, main_window: MainWindow) -> str:
        """Get the tooltip for the suggestion."""

    def make_executor(self, main_window: MainWindow) -> Callable[[], None]:
        """Create an executor for the suggestion."""
        return lambda: self.execute(main_window)


@dataclass
class CommandSuggestion(Suggestion):
    """Next action that is a command execution."""

    command_id: str
    """The ID of the command to execute."""

    def execute(self, main_window: MainWindow) -> None:
        main_window.exec_action(self.command_id)

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


@dataclass
class ActionHint:
    matcher: ActionMatcher
    """The matcher that determines if this action hint is applicable."""
    suggestion: Suggestion
    """The next action to take if this action hint is applicable."""


class ActionHintRegistry:
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

    def add_hint(self, matcher: ActionMatcher, suggestion: Suggestion) -> None:
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

    def iter_suggestion(
        self, model_type: str, step: WorkflowStep
    ) -> Iterator[Suggestion]:
        """Get a list of matchers that match the given model type and step."""
        for ancestor_type, hints in self._rough_map.items():
            if model_type.startswith(ancestor_type):
                for hint in hints:
                    if hint.matcher.match(model_type, step):
                        yield hint.suggestion


class ActionMatcherInterface:
    def __init__(self, reg: ActionHintRegistry, matcher: ActionMatcher):
        self._registry = reg
        self._matcher = matcher

    def add_command_suggestion(
        self,
        command_id: str,
    ) -> Self:
        """Add a suggestion to the registry."""
        suggestion = CommandSuggestion(command_id=command_id)
        self._registry.add_hint(self._matcher, suggestion)
        return self
