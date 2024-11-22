from typing import TYPE_CHECKING, Any
from pathlib import Path
from pydantic_compat import BaseModel, Field


if TYPE_CHECKING:
    from app_model import Application

    from himena.widgets import MainWindow
    from himena.types import WidgetDataModel


class MethodDescriptor(BaseModel):
    """A class that describes how a widget data model was created."""

    def get_model(self, app: "Application") -> "WidgetDataModel[Any]":
        raise NotImplementedError


class ProgramaticMethod(MethodDescriptor):
    """Describes that one was created programmatically."""


class LocalReaderMethod(MethodDescriptor):
    """Describes that one was read from a local source file."""

    path: Path
    plugin: str | None = Field(default=None)

    def get_model(self, app: "Application") -> "WidgetDataModel[Any]":
        """Get model by importing the reader plugin and actually read the file(s)."""
        from himena._utils import import_object
        from himena.io import PluginInfo
        from himena.types import WidgetDataModel

        if self.plugin is None:
            raise ValueError("No plugin found.")

        reader_provider = import_object(self.plugin)
        reader = reader_provider(self.path)
        model = reader(self.path)
        if not isinstance(model, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {model}")
        if model.method is None:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin),
            )
        return model


class ConverterMethod(MethodDescriptor):
    """Describes that one was converted from another widget data model."""

    originals: list[MethodDescriptor]
    command_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)


def dict_to_method(data: dict) -> MethodDescriptor:
    """Convert a dictionary to a method descriptor."""
    if data["type"] == "programatic":
        return ProgramaticMethod()
    if data["type"] == "local_reader":
        return LocalReaderMethod(path=Path(data["path"]), plugin=data["plugin"])
    if data["type"] == "converter":
        return ConverterMethod(
            originals=[dict_to_method(d) for d in data["originals"]],
            command_id=data["command_id"],
            parameters=data["parameters"],
        )
    raise ValueError(f"Unknown method type: {data['type']}")


def method_to_dict(method: MethodDescriptor) -> dict:
    """Convert a method descriptor to a dictionary."""
    if isinstance(method, ProgramaticMethod):
        return {"type": "programatic"}
    elif isinstance(method, LocalReaderMethod):
        return {
            "type": "local_reader",
            "path": str(method.path),
            "plugin": method.plugin,
        }
    elif isinstance(method, ConverterMethod):
        return {
            "type": "converter",
            "originals": [method_to_dict(m) for m in method.originals],
            "command_id": method.command_id,
            "parameters": method.parameters,
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
                choices=["Yes", "Select another path", "Cancel"],
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
