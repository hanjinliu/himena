import tempfile
from typing import Iterator, Literal, Any, TYPE_CHECKING
from pathlib import Path
import warnings
import subprocess

from pydantic_compat import Field
from himena.utils.misc import PluginInfo
from himena.workflow._base import WorkflowStep

if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    from himena.workflow import Workflow


class NoParentWorkflow(WorkflowStep):
    """Describes that one has no parent."""

    output_model_type: str | None = Field(default=None)

    def iter_parents(self) -> Iterator[int]:
        yield from ()


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
        from himena._providers import ReaderStore
        from himena.types import WidgetDataModel
        from himena.standards.model_meta import read_metadata

        store = ReaderStore.instance()
        model = store.run(self.path, plugin=self.plugin)
        if not isinstance(model, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {model}")
        if len(model.workflow) == 0:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin) if self.plugin else None,
            )
        if isinstance(self.path, Path):
            meta_path = self.path.with_name(self.path.name + ".himena-meta")
            if meta_path.exists():
                try:
                    model.metadata = read_metadata(meta_path)
                except Exception as e:
                    warnings.warn(
                        f"Failed to read metadata from {meta_path}: {e}",
                        RuntimeWarning,
                        stacklevel=2,
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

    def to_str(self) -> str:
        """Return the remote file path representation."""
        return f"{self.username}@{self.host}:{self.path.as_posix()}"

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        model = self.run()
        return model

    def run(self):
        from himena._providers import ReaderStore

        store = ReaderStore.instance()

        with tempfile.TemporaryDirectory() as tmpdir:
            dst_path = Path(tmpdir).joinpath(self.path.name)
            self.run_scp(dst_path)
            model = store.run(dst_path, plugin=self.plugin)
            model.title = self.path.name
        model.workflow = self.construct_workflow()
        return model

    def run_scp(self, dst_path: Path, stdout=None):
        """Run scp command to move the file from remote to local `dst_path`."""
        src = self.to_str()

        if self.wsl:
            drive = dst_path.drive
            wsl_root = Path("mnt") / drive.lower().rstrip(":")
            dst_pathobj_wsl = wsl_root / dst_path.relative_to(drive).as_posix()[1:]
            dst_wsl = "/" + dst_pathobj_wsl.as_posix()
            dst = dst_path.as_posix()
            args = ["wsl", "-e", "scp", src, dst_wsl]
        else:
            dst = dst_path.as_posix()
            args = ["scp", src, dst]
        subprocess.run(args, stdout=stdout)
        return None
