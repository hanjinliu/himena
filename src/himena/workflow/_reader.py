import tempfile
from typing import Iterator, Literal, Any, TYPE_CHECKING
from pathlib import Path
from pydantic_compat import Field
from himena.workflow._base import WorkflowStep

if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    from himena.workflow import Workflow


class NoParentWorkflow(WorkflowStep):
    """Describes that one has no parent."""

    output_model_type: str | None = Field(default=None)

    def iter_parents(self) -> Iterator[int]:
        yield from ()

    def construct_workflow(self) -> "Workflow":
        from himena.workflow import Workflow

        return Workflow(steps=[self])


class ProgrammaticMethod(NoParentWorkflow):
    """Describes that one was created programmatically."""

    type: Literal["programmatic"] = "programmatic"

    def _get_model_impl(self, wf):
        raise ValueError("Data was added programmatically, thus cannot be re-executed.")


class ReaderMethod(NoParentWorkflow):
    """Describes that one was read from a file."""

    plugin: str | None = Field(default=None)


class LocalReaderMethod(ReaderMethod):
    """Describes that one was read from a local source file."""

    type: Literal["local-reader"] = "local-reader"
    path: Path | list[Path]

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel[Any]":
        return self.run()

    def run(self) -> "WidgetDataModel[Any]":
        """Get model by importing the reader plugin and actually read the file(s)."""
        from himena._providers import PluginInfo
        from himena.types import WidgetDataModel
        from himena._providers import ReaderProviderStore

        store = ReaderProviderStore.instance()
        model = store.run(self.path, plugin=self.plugin)
        if not isinstance(model, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {model}")
        if len(model.workflow) == 0:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin) if self.plugin else None,
            )
        return model


class SCPReaderMethod(ReaderMethod):
    """Describes that one was read from a remote source file via scp command."""

    type: Literal["scp-reader"] = "scp-reader"
    host: str
    username: str
    path: Path
    wsl: bool = Field(default=False)

    @classmethod
    def from_str(
        cls,
        s: str,
        /,
        wsl: bool = False,
        output_model_type: str | None = None,
    ) -> "SCPReaderMethod":
        username, rest = s.split("@")
        host, path = rest.split(":")
        return cls(
            username=username,
            host=host,
            path=Path(path),
            wsl=wsl,
            output_model_type=output_model_type,
        )

    def _file_path_repr(self) -> str:
        return f"{self.username}@{self.host}:{self.path.as_posix()}"

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        model = self.run()
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
        model.workflow = self.construct_workflow()
        return model
