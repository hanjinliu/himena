import tempfile
from typing import Literal, Any
from pathlib import Path
from pydantic_compat import Field
from himena.workflow._base import Workflow, WorkflowList
from himena.types import WidgetDataModel


class ProgramaticMethod(Workflow):
    """Describes that one was created programmatically."""

    type: Literal["programatic"] = "programatic"


class ReaderMethod(Workflow):
    """Describes that one was read from a file."""

    plugin: str | None = Field(default=None)


class LocalReaderMethod(ReaderMethod):
    """Describes that one was read from a local source file."""

    type: Literal["local-reader"] = "local-reader"
    path: Path | list[Path]

    def get_model(self, wlist: "WorkflowList") -> "WidgetDataModel[Any]":
        """Get model by importing the reader plugin and actually read the file(s)."""
        from himena._utils import import_object
        from himena._providers import PluginInfo
        from himena.types import WidgetDataModel

        if self.plugin is None:
            raise ValueError("No plugin found.")

        reader_provider = import_object(self.plugin)
        reader = reader_provider(self.path)
        model = reader(self.path)
        if not isinstance(model, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {model}")
        if model.workflow is None:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin),
            )
        return model


class SCPReaderMethod(ReaderMethod):
    """Describes that one was read from a remote source file via scp command."""

    type: Literal["scp-reader"] = "scp-reader"
    host: str
    username: str
    path: Path
    wsl: bool = Field(default=False)

    def _file_path_repr(self) -> str:
        return f"{self.username}@{self.host}:{self.path.as_posix()}"

    def get_model(self, wlist: "WorkflowList") -> "WidgetDataModel":
        import subprocess
        from himena._providers import ReaderProviderStore

        store = ReaderProviderStore.instance()
        src = self._file_path_repr()

        with tempfile.TemporaryDirectory() as tmpdir:
            if self.wsl:
                dst_pathobj = Path(tmpdir).joinpath(self.path.name)
                drive = dst_pathobj.drive
                wsl_root = Path("mnt") / drive.lower().rstrip(":")
                dst_pathobj_wsl = (
                    wsl_root / dst_pathobj.relative_to(drive).as_posix()[1:]
                )
                dst_wsl = "/" + dst_pathobj_wsl.as_posix()
                dst = dst_pathobj.as_posix()
                args = ["wsl", "-e", "scp", src, dst_wsl]
            else:
                dst = Path(tmpdir).joinpath(self.path.name).as_posix()
                args = ["scp", src, dst]
            subprocess.run(args)
            model = store.run(Path(dst))
            model.title = self.path.name
        return model
