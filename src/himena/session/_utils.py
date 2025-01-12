from pathlib import Path
from himena.widgets import SubWindow
from himena import io_utils


def write_model_by_uuid(
    self: SubWindow, dirname: str | Path, plugin: str | None = None
) -> None:
    """Write the widget data to a file."""
    model = self.to_model()
    if model.extension_default is None:
        if model.extensions:
            ext = model.extensions[0]
        else:
            raise ValueError(
                "Could not determine the file extension to be used to save."
            )
    else:
        ext = model.extension_default
    filename = f"{self._identifier.hex}{ext}"
    # NOTE: default save path should not be updated, because the file is supposed to
    # be saved
    return io_utils.write(model, dirname / filename, plugin=plugin)
