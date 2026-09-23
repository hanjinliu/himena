from pathlib import Path
from himena import io_utils
from himena.standards import BaseMetadata, write_metadata
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

    _save_metadata(model.metadata, dirname, prefix, win.title)
    return save_path


def _get_save_path(model: WidgetDataModel, dirname: Path, prefix: str = "") -> Path:
    title = replace_invalid_characters(model.title or "")
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
    return dirname / f"{prefix}_{filename_stem}"


def write_metadata_by_title(
    win: SubWindow,
    dirname: str | Path,
    prefix: str = "",
) -> None:
    """Write model metadata to the default place."""
    model = win.to_model()
    dirname = Path(dirname)
    return _save_metadata(model.metadata, dirname, prefix, win.title)


def _save_metadata(metadata, dirname: Path, prefix: str, title: str):
    if isinstance(metadata, BaseMetadata):
        meta_name = f"{prefix}_{replace_invalid_characters(title)}.himena-meta"
        meta_dir = dirname / meta_name
        meta_dir.mkdir(exist_ok=True)
        write_metadata(metadata, meta_dir)
    return None


def find_by_prefix(dirname: Path, prefix: int | str, suffix: str = "") -> Path | None:
    """Find the file or directory named "{prefix}_*{suffix}" in the directory.

    File names are sanitized from the titles, so the original title stored in the
    session.yaml cannot be used to reconstruct the path. The index prefix is always
    unique in a directory, so it is used to find the path instead.
    """
    for path in dirname.glob(f"{prefix}_*{suffix}"):
        return path
    return None


PATTERN_NOT_ALLOWED = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")
MAX_NAME_LENGTH = 64


def replace_invalid_characters(title: str) -> str:
    """Convert a title into a string that can be safely used as a file name.

    Characters not allowed in file names are replaced with "_", and trailing dots and
    spaces (not allowed on Windows) are removed. Too long titles are truncated while
    keeping the extension. Different titles may be converted into the same string, but
    the index prefix added by the caller guarantees the uniqueness.
    """
    name = PATTERN_NOT_ALLOWED.sub("_", title).strip().rstrip(".")
    if len(name) > MAX_NAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) < 10:
            name = stem[: MAX_NAME_LENGTH - len(ext) - 1].rstrip(" .") + dot + ext
        else:
            name = name[:MAX_NAME_LENGTH].rstrip(" .")
    return name or "Untitled"
