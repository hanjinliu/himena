from contextlib import contextmanager
from typing import Iterable, Iterator, TYPE_CHECKING
from datetime import datetime as _datetime
import uuid

from pydantic import PrivateAttr
from pydantic_compat import BaseModel, Field


if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    import in_n_out as ino


class WorkflowStep(BaseModel):
    """The base class for a single step in a workflow."""

    type: str
    """Literal string that describes the type of the instance."""

    datetime: _datetime = Field(default_factory=_datetime.now)
    """The timestamp of the creation of this instance."""

    id: int = Field(default_factory=lambda: uuid.uuid1().int)
    """The unique identifier of the workflow step across runtime."""

    def iter_parents(self) -> Iterator[int]:
        raise NotImplementedError("This method must be implemented in a subclass.")

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        raise NotImplementedError("This method must be implemented in a subclass.")

    def get_model(self, wf: "Workflow") -> "WidgetDataModel":
        model = self._get_model_impl(wf)
        model.workflow = wf
        return model

    def get_model_with_traceback(self, wf: "Workflow") -> "WidgetDataModel":
        try:
            self._get_model_impl(wf)
        except Exception as e:
            raise ValueError(f"Failed to get model for {self!r}") from e

    def __repr_args__(self):  # simplify the repr output
        for arg in super().__repr_args__():
            if arg[0] in ("type", "datetime", "id"):
                continue
            yield arg

    def __str__(self):
        return repr(self)

    def _current_store(self) -> "ino.Store":
        from himena.widgets import current_instance

        return current_instance().model_app.injection_store


class Workflow(BaseModel):
    """Container of WorkflowStep instances.

    The data structure of a workflow is a directed acyclic graph. Each node is a
    WorkflowStep instance, and the edges are defined inside each CommandExecution
    instance. Each node is tagged with a unique ID named `id`, which is used as a
    mathematical identifier for the node.
    """

    nodes: list[WorkflowStep] = Field(default_factory=list)
    _model_cache: dict[int, "WidgetDataModel"] = PrivateAttr(default_factory=dict)
    _cahce_enabled: bool = PrivateAttr(default=False)

    def id_to_index_map(self) -> dict[int, int]:
        return {node.id: i for i, node in enumerate(self.nodes)}

    def filter(self, step: int) -> "Workflow":
        """Return another list that only contains the ancestors of the given ID."""
        id_to_index_map = self.id_to_index_map()
        index = id_to_index_map[step]
        indices = {index}
        all_descendant = [self.nodes[index]]
        while all_descendant:
            current = all_descendant.pop()
            for id_ in current.iter_parents():
                idx = id_to_index_map[id_]
                if idx in indices:
                    continue
                indices.add(idx)
                all_descendant.append(self.nodes[idx])
        indices = sorted(indices)
        out = Workflow(nodes=[self.nodes[i] for i in indices])
        out._cahce_enabled = self._cahce_enabled
        out._model_cache = self._model_cache  # NOTE: do not update, share the reference
        return out

    def __getitem__(self, index: int) -> WorkflowStep:
        return self.nodes[index]

    def last(self) -> WorkflowStep | None:
        if len(self.nodes) == 0:
            return None
        return self.nodes[-1]

    def last_id(self) -> int:
        if step := self.last():
            return step.id
        raise ValueError("Workflow is empty.")

    def model_for_id(self, id: int) -> "WidgetDataModel":
        if model := self._model_cache.get(id):
            return model
        for workflow in self.nodes:
            if workflow.id == id:
                model = workflow.get_model(self)
                if self._cahce_enabled:
                    self._model_cache[id] = model
                return model
        raise ValueError(f"Workflow with id {id} not found.")

    def __iter__(self):
        return iter(self.nodes)

    def __len__(self) -> int:
        return len(self.nodes)

    def with_step(self, step: WorkflowStep) -> "Workflow":
        if not isinstance(step, WorkflowStep):
            raise ValueError("Expected a Workflow instance.")
        # The added step is always a unique node.
        return Workflow(nodes=self.nodes + [step])

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
        id_found: set[int] = set()
        for workflow in workflows:
            for node in workflow:
                if node.id in id_found:
                    continue
                id_found.add(node.id)
                nodes.append(node)
        return Workflow(nodes=nodes)
