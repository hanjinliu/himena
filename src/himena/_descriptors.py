from typing import TYPE_CHECKING, Any, Literal, Union, cast
from pathlib import Path
from pydantic_compat import BaseModel, Field
import tempfile

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from himena.types import WidgetDataModel


class WorkflowNode(BaseModel):
    """A class that describes how a widget data model was created."""

    def get_model(self, ui: "MainWindow") -> "WidgetDataModel[Any]":
        raise NotImplementedError

    def _render_history(self) -> list[str]:
        """Return the history in a tree format."""
        return NotImplementedError

    def render_history(self) -> str:
        """Return the history in a string format."""
        lines = self._render_history()
        return "\n".join(lines)

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text("WorkflowNode(...)")
        else:
            p.text(self.render_history())


class ProgramaticMethod(WorkflowNode):
    """Describes that one was created programmatically."""

    def _render_history(self) -> list[str]:
        return ["Created programatically"]


class ReaderMethod(WorkflowNode):
    """Describes that one was read from a file."""

    plugin: str | None = Field(default=None)


class LocalReaderMethod(ReaderMethod):
    """Describes that one was read from a local source file."""

    path: Path | list[Path]

    def get_model(self, ui: "MainWindow") -> "WidgetDataModel[Any]":
        """Get model by importing the reader plugin and actually read the file(s)."""
        from himena._utils import import_object
        from himena._providers import PluginInfo
        from himena.types import WidgetDataModel

        if self.plugin is None:
            raise ValueError("No plugin found.")

        reader_provider = import_object(self.plugin)
        reader = reader_provider(self.path)
        model = reader(self.path)
        if not isinstance(model, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {model}")
        if model.workflow is None:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin),
            )
        return model

    def _render_history(self) -> list[str]:
        return [f"[Local file] {self.path}"]


class SCPReaderMethod(ReaderMethod):
    """Describes that one was read from a remote source file via scp command."""

    host: str
    username: str
    path: Path
    wsl: bool = Field(default=False)

    def _file_path_repr(self) -> str:
        return f"{self.username}@{self.host}:{self.path.as_posix()}"

    def get_model(self, ui: "MainWindow") -> "WidgetDataModel":
        import subprocess
        from himena._providers import ReaderProviderStore

        store = ReaderProviderStore.instance()
        src = self._file_path_repr()

        with tempfile.TemporaryDirectory() as tmpdir:
            if self.wsl:
                dst_pathobj = Path(tmpdir).joinpath(self.path.name)
                drive = dst_pathobj.drive
                wsl_root = Path("mnt") / drive.lower().rstrip(":")
                dst_pathobj_wsl = (
                    wsl_root / dst_pathobj.relative_to(drive).as_posix()[1:]
                )
                dst_wsl = "/" + dst_pathobj_wsl.as_posix()
                dst = dst_pathobj.as_posix()
                args = ["wsl", "-e", "scp", src, dst_wsl]
            else:
                dst = Path(tmpdir).joinpath(self.path.name).as_posix()
                args = ["scp", src, dst]
            subprocess.run(args)
            model = store.run(Path(dst))
            model.title = self.path.name
        return model

    def _render_history(self) -> list[str]:
        src = self._file_path_repr()
        return [f"[Remote file] {src}"]


class CommandParameterBase(BaseModel):
    """A class that describes a parameter of a command."""

    name: str
    value: Any


class UserParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a user."""

    type: Literal["user"] = "user"


class ModelParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a model."""

    type: Literal["model"] = "model"
    value: WorkflowNode


class WindowParameter(CommandParameterBase):
    """A class that describes a parameter that was set by a window."""

    type: Literal["window"] = "window"
    value: WorkflowNode


class ListOfModelParameter(CommandParameterBase):
    """A class that describes a list of model parameters."""

    type: Literal["list"] = "list"
    value: list[WorkflowNode]


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

_BRANCH = "  ├─"
_VLINE = "  │ "
_BRANCH_END = "  └─"
_SPACES = "    "


class CommandExecution(WorkflowNode):
    """Describes that one was created by a command."""

    command_id: str
    contexts: list[CommandParameterType] = Field(default_factory=list)
    parameters: list[CommandParameterType] = Field(default_factory=list)

    def _render_history(self) -> list[str]:
        lines = [f"[Command] {self.command_id}"]
        params_and_ctx = self.parameters + self.contexts
        prefixes = [_BRANCH] * (len(params_and_ctx) - 1) + [_BRANCH_END]
        for param, prefix in zip(params_and_ctx, prefixes):
            if isinstance(param, UserParameter):
                cur_lines = [f"[Parameter] {param.name}={param.value!r}"]
            elif isinstance(param, ModelParameter):
                cur_lines = param.value._render_history()
            elif isinstance(param, ListOfModelParameter):
                cur_lines = ["List of models:"]
                for model in param.value:
                    cur_lines.extend(model._render_history())
            else:
                raise ValueError(f"Unknown parameter type: {param}")
            num_cur_lines = len(cur_lines)
            if prefix == _BRANCH:
                cur_prefixes = [_BRANCH] + [_VLINE] * (num_cur_lines - 1)
            else:
                cur_prefixes = [_BRANCH_END] + [_SPACES] * (num_cur_lines - 1)
            hist = [
                f"{cur_prefix} {cur_line}"
                for cur_prefix, cur_line in zip(cur_prefixes, cur_lines)
            ]
            lines.extend(hist)
        return lines

    def get_model(self, ui: "MainWindow") -> "WidgetDataModel":
        from himena.types import WidgetDataModel

        model_context = None
        window_context = None
        for context in self.contexts:
            if isinstance(context, ModelParameter):
                model_context = context.value.get_model(ui)
            elif isinstance(context, WindowParameter):
                model_context = context.value.get_model(ui)
            else:
                raise ValueError(f"Context parameter must be a model: {context}")
            if not isinstance(context.value, CommandExecution):
                window_context = ui.add_data_model(model_context)

        action_params = {}
        for param in self.parameters:
            if isinstance(param, UserParameter):
                action_params[param.name] = param.value
            elif isinstance(param, ModelParameter):
                action_params[param.name] = param.value.get_model(ui)
            elif isinstance(param, ListOfModelParameter):
                action_params[param.name] = [each.get_model(ui) for each in param.value]
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


class UserModification(WorkflowNode):
    """Describes that one was modified from another model."""

    original: WorkflowNode

    def _render_history(self) -> list[str]:
        lines = self.original._render_history()
        prefixes = [_BRANCH_END] + [_SPACES] * (len(lines) - 1)
        return ["[Modified by User]"] + [
            f"{prefix} {line}" for prefix, line in zip(prefixes, lines)
        ]

    def get_model(self, ui: "MainWindow") -> "WidgetDataModel":
        # just skip modification...
        return self.original.get_model(ui)


def dict_to_workflow(data: dict) -> WorkflowNode:
    """Convert a dictionary to a method descriptor."""
    if data["type"] == "programatic":
        return ProgramaticMethod()
    if data["type"] == "local_reader":
        return LocalReaderMethod(path=Path(data["path"]), plugin=data["plugin"])
    if data["type"] == "scp_reader":
        return SCPReaderMethod(
            host=data["host"],
            username=data["username"],
            path=Path(data["path"]),
            wsl=data["wsl"],
        )
    if data["type"] == "user-edit":
        return UserModification(original=dict_to_workflow(data["original"]))
    if data["type"] == "command":
        return CommandExecution(
            command_id=data["command_id"],
            contexts=data["contexts"],
            parameters=data["parameters"],
        )
    raise ValueError(f"Unknown method type: {data['type']}")


def workflow_to_dict(method: WorkflowNode) -> dict:
    """Convert a method descriptor to a dictionary."""
    if isinstance(method, ProgramaticMethod):
        return {"type": "programatic"}
    elif isinstance(method, LocalReaderMethod):
        return {
            "type": "local_reader",
            "path": str(method.path),
            "plugin": method.plugin,
        }
    elif isinstance(method, SCPReaderMethod):
        return {
            "type": "scp_reader",
            "host": method.host,
            "username": method.username,
            "path": str(method.path),
            "wsl": method.wsl,
        }
    elif isinstance(method, CommandExecution):
        return {
            "type": "command",
            "command_id": method.command_id,
            "contexts": [m.model_dump() for m in method.contexts],
            "parameters": [m.model_dump() for m in method.parameters],
        }
    elif isinstance(method, UserModification):
        return {
            "type": "user-edit",
            "original": workflow_to_dict(method.original),
        }
    else:
        raise ValueError(f"Unknown method type: {method}")


class SaveBehavior(BaseModel):
    """A class that describes how a widget should be saved."""

    def get_save_path(
        self,
        main: "MainWindow",
        model: "WidgetDataModel",
    ) -> Path | None:
        """Return the path to save (None to cancel)."""
        return main.exec_file_dialog(
            mode="w",
            extension_default=model.extension_default,
            allowed_extensions=model.extensions,
            start_path=self._determine_save_path(model),
        )

    @staticmethod
    def _determine_save_path(model: "WidgetDataModel") -> str | None:
        if model.title is None:
            if model.extension_default is None:
                start_path = None
            else:
                start_path = f"Untitled{model.extension_default}"
        else:
            if Path(model.title).suffix in model.extensions:
                start_path = model.title
            elif model.extension_default is not None:
                start_path = Path(model.title).stem + model.extension_default
            else:
                start_path = model.title
        return start_path


class NoNeedToSave(SaveBehavior):
    """Describes that the widget does not need to be saved.

    This save behavior is usually used for commands that create a new data. Users will
    not be asked to save the data when they close the window, but will be asked if the
    data is modified.
    """


class CannotSave(SaveBehavior):
    """Describes that the widget cannot be saved."""

    reason: str

    def get_save_path(self, main, model):
        raise ValueError(f"Cannot save this widget: {self.reason}")


class SaveToNewPath(SaveBehavior):
    """Describes that the widget should be saved to a new path."""


class SaveToPath(SaveBehavior):
    """Describes that the widget should be saved to a specific path.

    A subwindow that has been saved once should always be tagged with this behavior.
    """

    path: Path
    ask_overwrite: bool = Field(
        default=True,
        description="Ask before overwriting the file if `path` already exists.",
    )
    plugin: str | None = Field(
        default=None,
        description="The plugin to use if the file is read back.",
    )

    def get_save_path(
        self,
        main: "MainWindow",
        model: "WidgetDataModel",
    ) -> Path | None:
        if self.path.exists() and self.ask_overwrite:
            res = main.exec_choose_one_dialog(
                title="Overwrite?",
                message=f"{self.path}\nalready exists, overwrite?",
                choices=["Overwrite", "Select another path", "Cancel"],
            )
            if res == "Cancel":
                return None
            elif res == "Select another path":
                if path := SaveToNewPath().get_save_path(main, model):
                    self.path = path
                else:
                    return None
            # If overwrite is allowed, don't ask again.
            self.ask_overwrite = False
        return self.path
