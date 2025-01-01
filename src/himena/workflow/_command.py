from typing import Literal, Any, cast, Union
from pydantic_compat import BaseModel, Field
from himena.workflow._base import Workflow, WorkflowList
from himena.workflow._reader import ProgramaticMethod
from himena.types import WidgetDataModel


class CommandParameterBase(BaseModel):
    """A class that describes a parameter of a command."""

    type: str
    name: str
    value: Any


class UserParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a user."""

    type: Literal["user"] = "user"


class ModelParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a model."""

    type: Literal["model"] = "model"
    value: int


class WindowParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a window."""

    type: Literal["window"] = "window"
    value: int


class ListOfModelParameter(CommandParameterBase):
    """A class that describes a list of model parameters."""

    type: Literal["list"] = "list"
    value: list[int]


def parse_parameter(name: str, value: Any) -> CommandParameterBase:
    from himena.types import WidgetDataModel
    from himena.widgets import SubWindow

    if isinstance(value, WidgetDataModel):
        if value.workflow is None:
            param = ModelParameter(name=name, value=ProgramaticMethod())
        else:
            param = ModelParameter(name=name, value=value.workflow)
    elif isinstance(value, SubWindow):
        meth = value.to_model().workflow
        if meth is None:
            param = WindowParameter(name=name, value=ProgramaticMethod())
        else:
            param = WindowParameter(name=name, value=meth)
    elif isinstance(value, list) and all(
        isinstance(each, (WidgetDataModel, SubWindow)) for each in value
    ):
        value_ = cast(list[WidgetDataModel], value)
        param = ListOfModelParameter(
            name=name, value=[each.workflow or ProgramaticMethod() for each in value_]
        )
    else:
        param = UserParameter(name=name, value=value)
    return param


CommandParameterType = Union[
    UserParameter, ModelParameter, WindowParameter, ListOfModelParameter
]


class CommandExecution(Workflow):
    """Describes that one was created by a command."""

    type: Literal["command"] = "command"
    command_id: str
    contexts: list[CommandParameterType] = Field(default_factory=list)
    parameters: list[CommandParameterType] = Field(default_factory=list)

    def get_model(self, wlist: WorkflowList) -> "WidgetDataModel":
        from himena.types import WidgetDataModel
        from himena.widgets import current_instance

        model_context = None
        window_context = None
        ui = current_instance()
        for context in self.contexts:
            if isinstance(context, ModelParameter):
                model_context = wlist[context.value].get_model(wlist)
            elif isinstance(context, WindowParameter):
                model_context = wlist[context.value].get_model(wlist)
            else:
                raise ValueError(f"Context parameter must be a model: {context}")
            if not isinstance(context.value, CommandExecution):
                window_context = ui.add_data_model(model_context)

        action_params = {}
        for param in self.parameters:
            if isinstance(param, UserParameter):
                action_params[param.name] = param.value
            elif isinstance(param, ModelParameter):
                action_params[param.name] = wlist[param.value].get_model(wlist)
            elif isinstance(param, ListOfModelParameter):
                action_params[param.name] = [
                    wlist[each].get_model(wlist) for each in param.value
                ]
            else:
                raise ValueError(f"Unknown parameter type: {param}")
        result = ui.exec_action(
            self.command_id,
            window_context=window_context,
            model_context=model_context,
            with_params=action_params,
        )
        if not isinstance(result, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {result}")
        return result


class UserModification(Workflow):
    """Describes that one was modified from another model."""

    type: Literal["user-modification"] = "user-modification"
    original: int

    def get_model(self, wlist: "WorkflowList") -> "WidgetDataModel":
        # just skip modification...
        return wlist[self.original].get_model(wlist)
