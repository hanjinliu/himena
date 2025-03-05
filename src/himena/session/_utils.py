from pathlib import Path
from himena import io_utils
from himena.standards.model_meta import BaseMetadata, write_metadata
from himena.types import WidgetDataModel
from himena.widgets import SubWindow
import re


def write_model_by_title(
    win: SubWindow,
    dirname: str | Path,
    plugin: str | None = None,
    prefix: str = "",
) -> Path:
    """Write the widget data to a file, return the saved file."""
    model = win.to_model()
    dirname = Path(dirname)
    save_path = _get_save_path(model, dirname, prefix)

    # NOTE: default save path should not be updated, because the file is supposed to
    # be saved
    io_utils.write(model, save_path, plugin=plugin)

    i_win = int(save_path.name.split("_", 1)[0])
    _save_metadata(model.metadata, dirname, f"{i_win}_{win.title}")
    return save_path


def _get_save_path(model: WidgetDataModel, dirname: Path, prefix: str = "") -> Path:
    title = model.title or "Untitled"
    if Path(title).suffix in model.extensions:
        filename_stem = title
    else:
        if model.extension_default is None:
            if model.extensions:
                ext = model.extensions[0]
            else:
                raise ValueError(
                    f"Could not determine the file extension to be used to save {model!r}"
                )
        else:
            ext = model.extension_default
        if title.endswith(ext):
            filename_stem = title
        else:
            filename_stem = f"{title}{ext}"
    filename = f"{prefix}_{replace_invalid_characters(filename_stem)}"
    return dirname / filename


def write_metadata_by_title(
    win: SubWindow,
    dirname: str | Path,
    prefix: str = "",
) -> Path:
    model = win.to_model()
    dirname = Path(dirname)
    save_path = _get_save_path(model, dirname, prefix)
    i_win = int(save_path.name.split("_", 1)[0])
    _save_metadata(model.metadata, dirname, f"{i_win}_{win.title}")
    return save_path


def _save_metadata(metadata, dirname: Path, title: str):
    if isinstance(metadata, BaseMetadata):
        meta_dir = dirname / f"{title}.himena-meta"
        meta_dir.mkdir(exist_ok=True)
        write_metadata(metadata, meta_dir)
    return None


PATTERN_NOT_ALLOWED = re.compile(r"[\\/:*?\"<>|]")


def replace_invalid_characters(title: str) -> str:
    return PATTERN_NOT_ALLOWED.sub("_", title)
