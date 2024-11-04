from typing import TYPE_CHECKING
from pathlib import Path
from pydantic_compat import BaseModel, Field

if TYPE_CHECKING:
    from royalapp.widgets import MainWindow


class MethodDescriptor(BaseModel):
    """A class that describes how a widget data model was created."""


class ProgramaticMethod(MethodDescriptor):
    """Describes that one was created programmatically."""


class LocalReaderMethod(MethodDescriptor):
    """Describes that one was read from a local source file."""

    path: Path
    plugin: str | None = Field(default=None)


class ConverterMethod(MethodDescriptor):
    """Describes that one was converted from another widget data model."""

    originals: list[MethodDescriptor]
    action_id: str


class SaveBehavior(BaseModel):
    """A class that describes how a widget should be saved."""

    def get_save_path(self, main: "MainWindow") -> Path | None:
        """Return the path to save (None to cancel)."""
        return main._backend_main_window._open_file_dialog(mode="w")


class SaveToNewPath(SaveBehavior):
    """Describes that the widget should be saved to a new path."""


class SaveToPath(SaveBehavior):
    """Describes that the widget should be saved to a specific path."""

    path: Path
    ask_overwrite: bool = Field(
        default=True,
        description="Ask before overwriting the file if `path` already exists.",
    )

    def get_save_path(self, main: "MainWindow") -> Path | None:
        if self.path.exists() and self.ask_overwrite:
            ok = main.exec_confirmation_dialog(
                f"{self.path} already exists, overwrite?"
            )
            if not ok:
                return None
        return self.path
