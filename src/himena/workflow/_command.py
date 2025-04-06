from concurrent.futures import Future
from typing import Iterator, Literal, Any, cast, Union, TYPE_CHECKING
import uuid
from pydantic_compat import BaseModel, Field
from himena.workflow._base import WorkflowStep

if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    from himena.workflow import Workflow


class CommandParameterBase(BaseModel):
    """A class that describes a parameter of a command."""

    type: str
    name: str
    value: Any

    def __repr_args__(self):
        for arg in super().__repr_args__():
            if arg[0] == "type":
                continue
            yield arg


class UserParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a user."""

    type: Literal["user"] = "user"
    value: Any
    """Any python object for this parameter"""


class ModelParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a model."""

    type: Literal["model"] = "model"
    value: uuid.UUID
    """workflow ID"""
    model_type: str


class WindowParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a window."""

    type: Literal["window"] = "window"
    value: uuid.UUID
    """workflow ID"""
    model_type: str


class ListOfModelParameter(CommandParameterBase):
    """A class that describes a list of model parameters."""

    type: Literal["list"] = "list"
    value: list[uuid.UUID]
    """workflow IDs"""


def parse_parameter(name: str, value: Any) -> "tuple[CommandParameterBase, Workflow]":
    """Normalize a k=v argument to a CommandParameterBase instance."""
    from himena.types import WidgetDataModel
    from himena.widgets import SubWindow
    from himena.workflow import Workflow

    if isinstance(value, WidgetDataModel):
        param = ModelParameter(
            name=name, value=value.workflow.last_id(), model_type=value.type
        )
        wf = value.workflow
    elif isinstance(value, SubWindow):
        model = value.to_model()
        wf = model.workflow
        param = WindowParameter(name=name, value=wf.last_id(), model_type=model.type)
    elif isinstance(value, list) and all(
        isinstance(each, (WidgetDataModel, SubWindow)) for each in value
    ):
        value_ = cast(list[WidgetDataModel], value)
        param = ListOfModelParameter(
            name=name, value=[each.workflow.last_id() for each in value_]
        )
        wf = Workflow.concat([each.workflow for each in value_])
    else:
        param = UserParameter(name=name, value=value)
        wf = Workflow()
    return param, wf


CommandParameterType = Union[
    UserParameter, ModelParameter, WindowParameter, ListOfModelParameter
]


class CommandExecution(WorkflowStep):
    """Describes that one was created by a command."""

    type: Literal["command"] = "command"
    command_id: str
    contexts: list[CommandParameterType] = Field(default_factory=list)
    parameters: list[CommandParameterType] | None = Field(
        default=None,
        description="Parameters passed to the command. None if the command is not parametric.",
    )
    execution_time: float = Field(default=0.0)  # seconds

    def iter_parents(self) -> Iterator[uuid.UUID]:
        for ctx in self.contexts:
            if isinstance(ctx, ModelParameter):
                yield ctx.value
            elif isinstance(ctx, WindowParameter):
                yield ctx.value

        for param in self.parameters or []:
            if isinstance(param, ModelParameter):
                yield param.value
            elif isinstance(param, ListOfModelParameter):
                yield from param.value

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        from himena.types import WidgetDataModel
        from himena.widgets import current_instance

        model_context = None
        window_context = None
        ui = current_instance()
        for _ctx in self.contexts:
            if isinstance(_ctx, ModelParameter):
                model_context = wf.model_for_id(_ctx.value)
            elif isinstance(_ctx, WindowParameter):
                window_context = wf.window_for_id(_ctx.value)
                model_context = window_context.to_model()
            else:
                raise ValueError(f"Context parameter must be a model: {_ctx}")

        if self.parameters is None:
            params = None
        else:
            params = {}
            for _p in self.parameters:
                if isinstance(_p, UserParameter):
                    params[_p.name] = _p.value
                elif isinstance(_p, ModelParameter):
                    params[_p.name] = wf.filter(_p.value).model_for_id(_p.value)
                elif isinstance(_p, WindowParameter):
                    params[_p.name] = wf.filter(_p.value).window_for_id(_p.value)
                elif isinstance(_p, ListOfModelParameter):
                    params[_p.name] = [
                        wf.filter(each).model_for_id(each) for each in _p.value
                    ]
                else:  # pragma: no cover
                    raise ValueError(f"Unknown parameter type: {_p}")
        result = ui.exec_action(
            self.command_id,
            window_context=window_context,
            model_context=model_context,
            with_params=params,
            process_model_output=False,
        )
        if isinstance(result, Future):
            result = result.result()
        if not isinstance(result, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {result}")
        return result


class UserModification(WorkflowStep):
    """Describes that one was modified from another model."""

    type: Literal["user-modification"] = "user-modification"
    original: uuid.UUID

    def _get_model_impl(self, sf: "Workflow") -> "WidgetDataModel":
        # just skip modification...
        return sf.model_for_id(self.original)

    def iter_parents(self) -> Iterator[uuid.UUID]:
        yield self.original
