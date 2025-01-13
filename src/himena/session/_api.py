from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
from uuid import UUID
import yaml
import zipfile
import tempfile
from himena.session._session import AppSession, TabSession
from himena.session._utils import write_model_by_uuid, num_digits
from himena.workflow import LocalReaderMethod

if TYPE_CHECKING:
    from himena.widgets import MainWindow

_ZIP_SESSION_YAML = "session.yaml"


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


def update_from_zip(ui: MainWindow, path: str | Path) -> None:
    with (
        zipfile.ZipFile(path) as z,
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        tmpdir = Path(tmpdir)
        z.extractall(tmpdir)
        with tmpdir.joinpath(_ZIP_SESSION_YAML).open("r") as f:
            yml = yaml.load(f, Loader=yaml.Loader)
        if not (isinstance(yml, dict) and "session" in yml):
            raise ValueError("Invalid session file.")
        if yml.pop("session") == "main":
            session = AppSession.model_validate(yml)
        else:
            raise ValueError("Invalid session file.")
        wf_overrides = {}
        for tab_dir in tmpdir.glob("Tab-*"):
            for file in tab_dir.iterdir():
                uuid_hex = file.stem.split("_")[-1]
                uuid = UUID(uuid_hex)
                wf_overrides[uuid] = LocalReaderMethod(path=file).construct_workflow()
        session.update_gui(ui, workflow_override=wf_overrides)
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


def dump_zip(ui: MainWindow, path: str | Path):
    """Dump the window state as a stand-alone zip file.

    The content will be something like:
    ```
    my.session.zip/
      ├── session.yaml
      └── Tab_0/
            ├── 00_xxx.txt
            ├── 01_yyy.csv
            :
    ```
    """
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmpdir, zipfile.ZipFile(path, "w") as z:
        tmpdir = Path(tmpdir)
        session = AppSession.from_gui(ui, allow_calculate=True)
        ndigits_tab = num_digits(len(ui.tabs))
        for i_tab, tab in enumerate(ui.tabs):
            dirname = f"Tab-{i_tab:>0{ndigits_tab}}"
            data_dir = tmpdir / dirname
            data_dir.mkdir()
            ndigits = num_digits(len(tab))
            for i, win in enumerate(tab):
                prefix = format(i, f">0{ndigits}")
                save_path = write_model_by_uuid(win, data_dir, prefix=prefix)
                z.write(save_path, f"{dirname}/{save_path.name}")

        js = session.model_dump(mode="json")
        js = {"session": "main", **js}
        z.writestr(_ZIP_SESSION_YAML, yaml.dump(js, sort_keys=False))
    return None
