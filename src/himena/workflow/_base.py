from typing import Sequence
from pydantic_compat import BaseModel
from himena.types import WidgetDataModel


class Workflow(BaseModel):
    parents: list[int]

    def get_model(self, ui: "WorkflowList") -> "WidgetDataModel":
        raise NotImplementedError("This method must be implemented in a subclass.")


class WorkflowList(Sequence[Workflow]):
    def __init__(self, workflows: list[Workflow]):
        self._list = workflows

    def filter(self, index: int) -> "WorkflowList":
        """Return another list that only contains the descendants of the given index."""
        indices = {index}
        all_descendant = [self._list[index]]
        while all_descendant:
            current = all_descendant.pop()
            for i in current.parents:
                if i in indices:
                    continue
                indices.add(i)
                all_descendant.append(self._list[i])
        indices = sorted(indices)
        return WorkflowList([self._list[i] for i in indices])

    def __getitem__(self, index: int) -> Workflow:
        return self._list[index]

    def __iter__(self):
        return iter(self._list)

    def __len__(self) -> int:
        return len(self._list)
