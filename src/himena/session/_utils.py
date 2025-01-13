from pathlib import Path
from himena.widgets import SubWindow
from himena import io_utils


def write_model_by_uuid(
    self: SubWindow,
    dirname: str | Path,
    plugin: str | None = None,
    prefix: str = "",
) -> Path:
    """Write the widget data to a file, return the saved file."""
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
    filename = f"{prefix}_{self._identifier.hex}{ext}"
    save_path = dirname / filename
    # NOTE: default save path should not be updated, because the file is supposed to
    # be saved
    io_utils.write(model, save_path, plugin=plugin)
    return save_path


def num_digits(n: int) -> int:
    return len(str(n - 1))
