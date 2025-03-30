from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Sequence
from pathlib import Path
import warnings
import yaml
import zipfile
import tempfile
from himena.session._session import AppSession, TabSession
from himena.session._utils import (
    write_model_by_title,
    write_metadata_by_title,
    replace_invalid_characters,
)
from himena.standards import read_metadata
from himena.widgets._wrapper import ParametricWindow
from himena.workflow import LocalReaderMethod
from himena.workflow._command import CommandExecution

if TYPE_CHECKING:
    from uuid import UUID
    from himena.widgets import MainWindow, TabArea

_SESSION_YAML = "session.yaml"


def update_from_directory(ui: MainWindow, path: str | Path) -> None:
    dirpath = Path(path)
    with dirpath.joinpath(_SESSION_YAML).open("r") as f:
        yml = yaml.load(f, Loader=yaml.Loader)
    if not (isinstance(yml, dict) and "session" in yml):
        raise ValueError("Invalid session file.")
    wf_overrides = {}
    if yml.pop("session") == "main":
        session = AppSession.model_validate(yml)
        for tab_dir in dirpath.iterdir():
            if tab_dir.is_file():
                continue
            ith = int(tab_dir.stem.split("_")[0])
            for uuid, meth in _iter_reader_method(tab_dir, session.tabs[ith]):
                wf_overrides[uuid] = meth
        session.update_gui(ui, workflow_override=wf_overrides, dirpath=dirpath)
    else:
        session = TabSession.model_validate(yml)
        wf_overrides = dict(_iter_reader_method(dirpath, session))
        session.update_gui(ui, workflow_override=wf_overrides, dirpath=dirpath)
    return None


def _iter_reader_method(
    dirpath: Path,
    tab_session: TabSession,
) -> Iterator[tuple[UUID, LocalReaderMethod]]:
    for file in dirpath.iterdir():
        if file.suffix == ".himena-meta":
            continue
        ith_win = int(file.stem.rsplit("_")[0])
        win_sess = tab_session.windows[ith_win]
        uuid = win_sess.id
        meta_path = file.with_name(f"{ith_win}_{win_sess.title}.himena-meta")
        metadata = None
        if meta_path.exists():
            try:
                metadata = read_metadata(meta_path)
            except Exception as e:
                warnings.warn(
                    f"Failed to read metadata from {meta_path}: {e}",
                    RuntimeWarning,
                    stacklevel=2,
                )
        meth = LocalReaderMethod(path=file, metadata_override=metadata)
        yield uuid, meth.construct_workflow()


def update_from_zip(ui: MainWindow, path: str | Path) -> None:
    with (
        zipfile.ZipFile(path) as z,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        tmpdir = Path(tmpdir)
        z.extractall(tmpdir)
        update_from_directory(ui, tmpdir)
    return None


def dump_tab_to_directory(
    tab: TabArea,
    path: str | Path,
    save_copies: bool = False,
    allow_calculate: Sequence[str] = (),
):
    path = Path(path)
    path.mkdir(exist_ok=True)
    session = TabSession.from_gui(tab, allow_calculate=True)
    cmd_id_allowed = set(allow_calculate)
    with open(path / _SESSION_YAML, "w") as f:
        js = session.model_dump(mode="json")
        js = {"session": "tab", **js}
        yaml.dump(js, f, sort_keys=False)
    _dump_tab_to_directory_impl(tab, path, save_copies, cmd_id_allowed)


def dump_tab_to_zip(
    tab: TabArea,
    path: str | Path,
    save_copies: bool = False,
    allow_calculate: Sequence[str] = (),
):
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmpdir, zipfile.ZipFile(path, "w") as z:
        tmpdir = Path(tmpdir)
        dump_tab_to_directory(
            tab, tmpdir, save_copies=save_copies, allow_calculate=allow_calculate
        )
        for file in tmpdir.rglob("*"):
            z.write(file, file.relative_to(tmpdir))
    return None


def _dump_tab_to_directory_impl(
    tab: TabArea,
    dirname: Path,
    save_copies: bool,
    cmd_id_allowed: set[str],
):
    for i, win in enumerate(tab):
        if isinstance(win, ParametricWindow):
            continue
        prefix = str(i)
        read_from = win._determine_read_from()
        if read_from is not None and isinstance(read_from[0], Path) and not save_copies:
            write_metadata_by_title(win, dirname, prefix)
        elif (
            isinstance(step := win._widget_workflow.last(), CommandExecution)
            and step.command_id in cmd_id_allowed
        ):
            write_metadata_by_title(win, dirname, prefix)
        elif win.supports_to_model and win.supports_update_model:
            write_model_by_title(win, dirname, prefix=prefix)
        else:
            # Cannot read or write the window state, must rely on command execution
            write_metadata_by_title(win, dirname, prefix)


def dump_directory(
    ui: MainWindow,
    path: str | Path,
    save_copies: bool = False,
    allow_calculate: Sequence[str] = (),
):
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
    cmd_id_allowed = set(allow_calculate)
    with open(path / _SESSION_YAML, "w") as f:
        js = session.model_dump(mode="json")
        js = {"session": "main", **js}
        yaml.dump(js, f, sort_keys=False)
    for i_tab, tab in enumerate(ui.tabs):
        tab_title = replace_invalid_characters(tab.title)
        dirname = path / f"{i_tab}_{tab_title}"
        dirname.mkdir()
        _dump_tab_to_directory_impl(tab, dirname, save_copies, cmd_id_allowed)
    return None


def dump_zip(
    ui: MainWindow,
    path: str | Path,
    save_copies: bool = False,
    allow_calculate: Sequence[str] = (),
):
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
        dump_directory(
            ui, tmpdir, save_copies=save_copies, allow_calculate=allow_calculate
        )
        for file in tmpdir.rglob("*"):
            z.write(file, file.relative_to(tmpdir))
    return None
