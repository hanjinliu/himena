from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
import yaml
import zipfile
import tempfile
from himena.session._session import AppSession, TabSession
from himena.session._utils import (
    write_model_by_title,
    num_digits,
    replace_invalid_characters,
)
from himena.workflow import LocalReaderMethod

if TYPE_CHECKING:
    from himena.widgets import MainWindow

_SESSION_YAML = "session.yaml"


def from_yaml(path: str | Path) -> AppSession | TabSession:
    with open(path) as f:
        yml = yaml.load(f, Loader=yaml.Loader)
    if not (isinstance(yml, dict) and "session" in yml):
        raise ValueError("Invalid session file.")
    session_type = yml.pop("session")
    if session_type == "main":
        return AppSession.model_validate(yml)
    elif session_type == "tab":
        return TabSession.model_validate(yml)
    else:
        raise ValueError("Invalid session file.")


def update_from_directory(ui: MainWindow, path: str | Path) -> None:
    dirpath = Path(path)
    with dirpath.joinpath(_SESSION_YAML).open("r") as f:
        yml = yaml.load(f, Loader=yaml.Loader)
    if not (isinstance(yml, dict) and "session" in yml):
        raise ValueError("Invalid session file.")
    if yml.pop("session") == "main":
        session = AppSession.model_validate(yml)
    else:
        raise ValueError("Invalid session file.")
    wf_overrides = {}
    for tab_dir in dirpath.iterdir():
        if tab_dir.is_file():
            continue
        ith = int(tab_dir.stem.split("_")[0])
        for file in tab_dir.iterdir():
            if file.suffix == ".himena-meta":
                continue
            ith_win = int(file.stem.rsplit("_")[0])
            uuid = session.tabs[ith].windows[ith_win].id
            wf_overrides[uuid] = LocalReaderMethod(path=file).construct_workflow()
    session.update_gui(ui, workflow_override=wf_overrides)
    return None


def update_from_zip(ui: MainWindow, path: str | Path) -> None:
    with (
        zipfile.ZipFile(path) as z,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        tmpdir = Path(tmpdir)
        z.extractall(tmpdir)
        update_from_directory(ui, tmpdir)
    return None


def dump_yaml(
    ui: MainWindow,
    path: str | Path,
    *,
    allow_calculate: bool = False,
) -> None:
    """Save the current session to a file."""
    path = Path(path)
    session = AppSession.from_gui(ui, allow_calculate=allow_calculate)
    js = session.model_dump(mode="json")
    js = {"session": "main", **js}
    with path.open("w") as f:
        yaml.dump(js, f, sort_keys=False)
    return None


def dump_directory(ui: MainWindow, path: str | Path):
    """Dump the main window state as a directory.

    The content will be something like:
    ```
    my_session_directory/
      ├── session.yaml
      └── 0_tab_name/
            ├── 00_xxx.txt
            ├── 01_yyy.csv
            :
    ```
    """
    path = Path(path)
    path.mkdir(exist_ok=True)
    session = AppSession.from_gui(ui, allow_calculate=True)
    with open(path / _SESSION_YAML, "w") as f:
        js = session.model_dump(mode="json")
        js = {"session": "main", **js}
        yaml.dump(js, f, sort_keys=False)
    ndigits_tab = num_digits(len(ui.tabs))
    for i_tab, tab in enumerate(ui.tabs):
        tab_title = replace_invalid_characters(tab.title)
        dirname = path / f"{i_tab:>0{ndigits_tab}}_{tab_title}"
        dirname.mkdir()
        ndigits = num_digits(len(tab))
        for i, win in enumerate(tab):
            prefix = format(i, f">0{ndigits}")
            write_model_by_title(win, dirname, prefix=prefix)
    return None


def dump_zip(ui: MainWindow, path: str | Path):
    """Dump the main window state as a stand-alone zip file.

    The content will be something like:
    ```
    my.session.zip/
      ├── session.yaml
      └── 0_tab_name/
            ├── 00_xxx.txt
            ├── 01_yyy.csv
            :
    ```
    """
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmpdir, zipfile.ZipFile(path, "w") as z:
        tmpdir = Path(tmpdir)
        dump_directory(ui, tmpdir)
        for file in tmpdir.rglob("*"):
            z.write(file, file.relative_to(tmpdir))
    return None
