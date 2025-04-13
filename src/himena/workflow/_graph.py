from contextlib import contextmanager
from typing import Iterable, TYPE_CHECKING, Union
import uuid

from pydantic import PrivateAttr
from pydantic_compat import BaseModel, Field

from himena.workflow._base import WorkflowStep
from himena.workflow._reader import (
    ProgrammaticMethod,
    LocalReaderMethod,
    RemoteReaderMethod,
    UserInput,
)
from himena.workflow._command import CommandExecution, UserModification

if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    from himena.mock import MainWindowMock
    from himena.mock.widget import MockWidget
    from himena.widgets import SubWindow

WorkflowStepType = Union[
    ProgrammaticMethod,
    LocalReaderMethod,
    RemoteReaderMethod,
    CommandExecution,
    UserModification,
    UserInput,
]


def _make_mock_main_window():
    from himena.mock import MainWindowMock
    from himena._app_model import get_model_app
    from himena.style import default_style

    return MainWindowMock(get_model_app("."), default_style())


class Workflow(BaseModel):
    """Container of WorkflowStep instances.

    The data structure of a workflow is a directed acyclic graph. Each node is a
    WorkflowStep instance, and the edges are defined inside each CommandExecution
    instance. Each node is tagged with a unique ID named `id`, which is used as a
    mathematical identifier for the node.
    """

    steps: list[WorkflowStepType] = Field(default_factory=list)
    _mock_main_window: "MainWindowMock" = PrivateAttr(
        default_factory=_make_mock_main_window
    )
    _cache_enabled: bool = PrivateAttr(default=False)

    def id_to_index_map(self) -> dict[uuid.UUID, int]:
        return {step.id: i for i, step in enumerate(self.steps)}

    def filter(self, step: uuid.UUID) -> "Workflow":
        """Return another workflow that only contains the ancestors of the given ID.

        For example, if the workflow is:

        ```
        W0 -> W1 -> W2 -> W3
              ^
              |
        W2 ---+
        ```

        and the given ID is W1, then the returned workflow will be:

        ```
        W0 -> W1
              ^
              |
        W2 ---+
        ```

        """
        indices = sorted(self._get_ancestors(step)[0])
        out = Workflow(steps=[self.steps[i] for i in indices])
        out._cache_enabled = self._cache_enabled
        out._mock_main_window = (
            self._mock_main_window
        )  # NOTE: do not update, share the reference
        # out._model_cache = self._model_cache  # NOTE: do not update, share the reference
        return out

    def __getitem__(self, index: int) -> WorkflowStep:
        return self.steps[index]

    def last(self) -> WorkflowStep | None:
        """Get the last step if exists."""
        if len(self.steps) == 0:
            return None
        return self.steps[-1]

    def last_id(self) -> uuid.UUID:
        """Get the ID of the last step."""
        if step := self.last():
            return step.id
        raise ValueError("Workflow is empty.")

    def deep_copy(self) -> "Workflow":
        return Workflow(steps=[step.model_copy() for step in self.steps])

    def index_for_id(self, id: uuid.UUID) -> int:
        for index, step in enumerate(self.steps):
            if step.id == id:
                return index
        raise ValueError(f"Workflow with id {id} not found.")

    def step_for_id(self, id: uuid.UUID) -> WorkflowStep:
        return self.steps[self.index_for_id(id)]

    def window_for_id(self, id: uuid.UUID) -> "SubWindow[MockWidget]":
        """Get the sub-window for the given ID."""
        if win := self._mock_main_window.window_for_id(id):
            return win
        step = self.step_for_id(id)
        model = step.get_model(self)
        if self._cache_enabled:
            win = self._mock_main_window.add_data_model(model)
            win._identifier = id
            return win
        raise ValueError("Window input cannot be resolved in this context.")

    def model_for_id(self, id: uuid.UUID) -> "WidgetDataModel":
        """Get the widget data model for the given ID."""
        if win := self._mock_main_window.window_for_id(id):
            return win.to_model()
        step = self.step_for_id(id)
        model = step.get_model(self)
        if self._cache_enabled:
            win = self._mock_main_window.add_data_model(model)
            win._identifier = id
        return model

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    def with_step(
        self,
        step: WorkflowStepType,
        *,
        after: uuid.UUID | None = None,
    ) -> "Workflow":
        """Return a new workflow with the given step added."""
        if not isinstance(step, WorkflowStep):
            raise ValueError("Expected a Workflow instance.")
        # The added step is always a unique node.
        if after is None:
            steps_new = self.steps + [step]
        else:
            steps_new = self.steps.copy()
            steps_new.insert(self.index_for_id(after) + 1, step)
        return Workflow(steps=steps_new)

    def compute(self, process_output: bool = True) -> "WidgetDataModel":
        """Compute the last node in the workflow."""
        with self._cache_context():
            out = self[-1].get_model(self, force_process_output=process_output)
        return out

    @contextmanager
    def _cache_context(self):
        """Cache the intermediate results in this context.

        For example, if the workflow is `A -> B0`, `A -> B1`, `B0, B1 -> C`, then
        the result of `A` will be cached and reused when computing `B0` and `B1`.
        """
        was_enabled = self._cache_enabled
        self._cache_enabled = True
        try:
            yield
        finally:
            self._cache_enabled = was_enabled
            if not was_enabled:
                self._mock_main_window.clear()

    @classmethod
    def concat(cls, workflows: Iterable["Workflow"]) -> "Workflow":
        """Concatenate multiple workflows and drop duplicate nodes based on the ID."""
        nodes: list[WorkflowStep] = []
        id_found: set[uuid.UUID] = set()
        for workflow in workflows:
            for node in workflow:
                if node.id in id_found:
                    continue
                id_found.add(node.id)
                nodes.append(node)
        return Workflow(steps=nodes)

    def replace(
        self,
        step: uuid.UUID,
        new: "WorkflowStep | Workflow",
    ) -> "Workflow":
        """Replace the step of the given ID with the new step."""
        indices, index = self._get_ancestors(step, exclude_me=True)
        new_steps = self.steps.copy()
        indices_to_remove = sorted(indices, reverse=True)
        for i in indices_to_remove:
            new_steps.pop(i)
        index_shifted = index - len([i for i in indices_to_remove if i < index])
        if isinstance(new, WorkflowStep):
            new_steps[index_shifted] = new
            new.id = step
        elif isinstance(new, Workflow):
            insert = new.steps.copy()
            if len(insert) == 0:
                raise ValueError("Input workflow is empty.")
            insert[-1] = insert[-1].model_copy(update={"id": step})
            new_steps = (
                new_steps[:index_shifted] + insert + new_steps[index_shifted + 1 :]
            )
        else:
            raise TypeError(f"Expected a WorkflowStep or Workflow, got {type(new)}.")
        return Workflow(steps=new_steps)

    def replace_with_input(
        self,
        step: uuid.UUID,
        how: str = "model",
    ) -> "Workflow":
        """Replace the step of the given ID with a runtime input."""
        new_step = UserInput(how=how)  # TODO: restrict input type
        return self.replace(step, new_step)

    def _get_ancestors(
        self,
        step: uuid.UUID,
        exclude_me: bool = False,
    ) -> tuple[set[int], int]:
        id_to_index_map = self.id_to_index_map()
        index = id_to_index_map[step]

        indices = {index}
        ancestors = [self.steps[index]]
        while ancestors:
            current = ancestors.pop()
            for id_ in current.iter_parents():
                idx = id_to_index_map[id_]
                if idx in indices:
                    continue
                indices.add(idx)
                ancestors.append(self.steps[idx])
        if exclude_me:
            indices.remove(index)
        return indices, index


def compute(workflows: list[Workflow]) -> list["WidgetDataModel | Exception"]:
    """Compute all the workflow with the shared cache."""
    if len(workflows) == 0:
        return []
    _global_ui = _make_mock_main_window()
    results: list["WidgetDataModel"] = []
    all_workflows = Workflow.concat(workflows)
    # share the cache
    for workflow in workflows:
        workflow._mock_main_window = _global_ui
    with all_workflows._cache_context():
        for workflow in workflows:
            try:
                result = workflow.compute(process_output=False)
            except Exception as e:
                result = e
            results.append(result)
    _global_ui.clear()
    for workflow in workflows:
        workflow._mock_main_window = _make_mock_main_window()
    return results


def is_reproducible(workflows: list[Workflow]) -> list[bool]:
    if len(workflows) == 0:
        return []
    _global_cache: dict[uuid.UUID, bool] = {}

    def _is_reproducible(
        step: WorkflowStep,
        id_to_index_map: dict[uuid.UUID, int],
    ) -> bool:
        parents = list(step.iter_parents())
        if len(parents) == 0:
            return isinstance(step, LocalReaderMethod)
        for parent in parents:
            if parent not in _global_cache:
                idx = id_to_index_map[parent]
                _global_cache[parent] = _is_reproducible(
                    workflows[idx], id_to_index_map
                )
            rep = _global_cache[parent]
            if not rep:
                return False
        return True

    results: list[bool] = []
    for workflow in workflows:
        results.append(all(_is_reproducible(step) for step in workflow.steps))
    return results
