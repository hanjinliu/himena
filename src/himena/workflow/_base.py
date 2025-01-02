from typing import Iterator, TYPE_CHECKING
from datetime import datetime as _datetime
import uuid

from pydantic_compat import BaseModel, Field


if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    from himena.workflow import Workflow
    import in_n_out as ino


class WorkflowStep(BaseModel):
    """The base class for a single step in a workflow."""

    type: str
    """Literal string that describes the type of the instance."""

    datetime: _datetime = Field(default_factory=_datetime.now)
    """The timestamp of the creation of this instance."""

    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
    """The unique identifier of the workflow step across runtime."""

    def iter_parents(self) -> Iterator[uuid.UUID]:
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