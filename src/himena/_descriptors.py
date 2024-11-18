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
        )


class SaveToNewPath(SaveBehavior):
    """Describes that the widget should be saved to a new path."""


class SaveToPath(SaveBehavior):
    """Describes that the widget should be saved to a specific path."""

    path: Path
    ask_overwrite: bool = Field(
        default=True,
        description="Ask before overwriting the file if `path` already exists.",
    )

    def get_save_path(
        self,
        main: "MainWindow",
        model: "WidgetDataModel",
    ) -> Path | None:
        if self.path.exists() and self.ask_overwrite:
            ok = main.exec_confirmation_dialog(
                f"{self.path} already exists, overwrite?"
            )
            if not ok:
                return None
            # If overwrite is allowed, don't ask again.
            self.ask_overwrite = False
        return self.path
