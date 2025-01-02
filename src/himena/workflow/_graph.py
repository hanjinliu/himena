from contextlib import contextmanager
from typing import Iterable, TYPE_CHECKING, Union
import uuid

from pydantic import PrivateAttr
from pydantic_compat import BaseModel, Field

from himena.workflow._base import WorkflowStep
from himena.workflow._reader import (
    ProgrammaticMethod,
    LocalReaderMethod,
    SCPReaderMethod,
)
from himena.workflow._command import CommandExecution, UserModification

if TYPE_CHECKING:
    from himena.types import WidgetDataModel

WorkflowStepType = Union[
    ProgrammaticMethod,
    LocalReaderMethod,
    SCPReaderMethod,
    CommandExecution,
    UserModification,
]


class Workflow(BaseModel):
    """Container of WorkflowStep instances.

    The data structure of a workflow is a directed acyclic graph. Each node is a
    WorkflowStep instance, and the edges are defined inside each CommandExecution
    instance. Each node is tagged with a unique ID named `id`, which is used as a
    mathematical identifier for the node.
    """

    steps: list[WorkflowStepType] = Field(default_factory=list)
    _model_cache: dict[int, "WidgetDataModel"] = PrivateAttr(default_factory=dict)
    _cahce_enabled: bool = PrivateAttr(default=False)

    def id_to_index_map(self) -> dict[uuid.UUID, int]:
        return {node.id: i for i, node in enumerate(self.steps)}

    def filter(self, step: uuid.UUID) -> "Workflow":
        """Return another list that only contains the ancestors of the given ID."""
        id_to_index_map = self.id_to_index_map()
        index = id_to_index_map[step]
        indices = {index}
        all_descendant = [self.steps[index]]
        while all_descendant:
            current = all_descendant.pop()
            for id_ in current.iter_parents():
                idx = id_to_index_map[id_]
                if idx in indices:
                    continue
                indices.add(idx)
                all_descendant.append(self.steps[idx])
        indices = sorted(indices)
        out = Workflow(steps=[self.steps[i] for i in indices])
        out._cahce_enabled = self._cahce_enabled
        out._model_cache = self._model_cache  # NOTE: do not update, share the reference
        return out

    def __getitem__(self, index: int) -> WorkflowStep:
        return self.steps[index]

    def last(self) -> WorkflowStep | None:
        if len(self.steps) == 0:
            return None
        return self.steps[-1]

    def last_id(self) -> uuid.UUID:
        if step := self.last():
            return step.id
        raise ValueError("Workflow is empty.")

    def model_for_id(self, id: uuid.UUID) -> "WidgetDataModel":
        if model := self._model_cache.get(id):
            return model
        for workflow in self.steps:
            if workflow.id == id:
                model = workflow.get_model(self)
                if self._cahce_enabled:
                    self._model_cache[id] = model
                return model
        raise ValueError(f"Workflow with id {id} not found.")

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    def with_step(self, step: WorkflowStep) -> "Workflow":
        if not isinstance(step, WorkflowStep):
            raise ValueError("Expected a Workflow instance.")
        # The added step is always a unique node.
        return Workflow(steps=self.steps + [step])

    def get_model(self) -> "WidgetDataModel":
        with self._cache_context():
            return self[-1].get_model_with_traceback(self)

    @contextmanager
    def _cache_context(self):
        was_enabled = self._cahce_enabled
        self._cahce_enabled = True
        try:
            yield
        finally:
            self._cahce_enabled = was_enabled
            self._model_cache.clear()

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
