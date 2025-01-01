import tempfile
from typing import Iterator, Literal, Any, TYPE_CHECKING
from pathlib import Path
from pydantic_compat import Field
from himena.workflow._base import WorkflowStep, Workflow

if TYPE_CHECKING:
    from himena.types import WidgetDataModel


class NoParentWorkflow(WorkflowStep):
    """Describes that one has no parent."""

    def iter_parents(self) -> Iterator[int]:
        yield from ()


class ProgramaticMethod(NoParentWorkflow):
    """Describes that one was created programmatically."""

    type: Literal["programatic"] = "programatic"


class ReaderMethod(NoParentWorkflow):
    """Describes that one was read from a file."""

    plugin: str | None = Field(default=None)


class LocalReaderMethod(ReaderMethod):
    """Describes that one was read from a local source file."""

    type: Literal["local-reader"] = "local-reader"
    path: Path | list[Path]

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel[Any]":
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
        if len(model.workflow) == 0:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin),
            )
        self._current_store().process(model, type_hint=WidgetDataModel)
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

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        model = self.run()
        self._current_store().process(model, type_hint=WidgetDataModel)
        return model

    def run(self):
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
            model = store.run(Path(dst), plugin=self.plugin)
            model.title = self.path.name
        model.workflow = Workflow(nodes=[self])
        return model
