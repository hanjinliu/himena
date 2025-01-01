from typing import TYPE_CHECKING
from pathlib import Path
from pydantic_compat import BaseModel, Field

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from himena.types import WidgetDataModel


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
