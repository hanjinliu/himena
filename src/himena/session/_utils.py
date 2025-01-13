from pathlib import Path
from himena import io_utils
from himena.standards.model_meta import BaseMetadata, write_metadata
from himena.widgets import SubWindow
import re


def write_model_by_title(
    self: SubWindow,
    dirname: str | Path,
    plugin: str | None = None,
    prefix: str = "",
) -> Path:
    """Write the widget data to a file, return the saved file."""
    model = self.to_model()
    dirname = Path(dirname)
    title = model.title or "Untitled"
    if Path(title).suffix in model.extensions:
        filename_stem = title
    else:
        if model.extension_default is None:
            if model.extensions:
                ext = model.extensions[0]
            else:
                raise ValueError(
                    "Could not determine the file extension to be used to save."
                )
        else:
            ext = model.extension_default
        if title.endswith(ext):
            filename_stem = title
        else:
            filename_stem = f"{title}{ext}"
    filename = f"{prefix}_{replace_invalid_characters(filename_stem)}"
    save_path = dirname / filename
    # NOTE: default save path should not be updated, because the file is supposed to
    # be saved
    io_utils.write(model, save_path, plugin=plugin)

    if isinstance(metadata := model.metadata, BaseMetadata):
        meta_dir = dirname / f"{filename}.himena-meta"
        meta_dir.mkdir(exist_ok=True)
        write_metadata(metadata, meta_dir)
    return save_path


PATTERN_NOT_ALLOWED = re.compile(r"[\\/:*?\"<>|]")


def replace_invalid_characters(title: str) -> str:
    return PATTERN_NOT_ALLOWED.sub("_", title)


def num_digits(n: int) -> int:
    return len(str(n - 1))
