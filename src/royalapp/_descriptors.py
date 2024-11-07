from typing import TYPE_CHECKING, Any
from pathlib import Path
from pydantic_compat import BaseModel, Field


if TYPE_CHECKING:
    from app_model import Application

    from royalapp.widgets import MainWindow
    from royalapp.types import WidgetDataModel


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
        from importlib import import_module

        if self.plugin is None:
            raise ValueError("No plugin found.")

        mod_name, func_name = self.plugin.rsplit(".", 1)
        mod = import_module(mod_name)
        func = getattr(mod, func_name)
        return func(self.path)


class ConverterMethod(MethodDescriptor):
    """Describes that one was converted from another widget data model."""

    originals: list[MethodDescriptor]
    action_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class SaveBehavior(BaseModel):
    """A class that describes how a widget should be saved."""

    def get_save_path(
        self,
        main: "MainWindow",
        model: "WidgetDataModel",
    ) -> Path | None:
        """Return the path to save (None to cancel)."""
        return main._backend_main_window._open_file_dialog(
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
        return self.path
