import tempfile
from typing import Iterator, Literal, Any, TYPE_CHECKING
from pathlib import Path
import warnings
import subprocess

from pydantic_compat import Field
from himena.utils.misc import PluginInfo
from himena.utils.cli import remote_to_local
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

    def run(self) -> "WidgetDataModel":
        raise NotImplementedError


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


class RemoteReaderMethod(ReaderMethod):
    """Describes that one was read from a remote source file."""

    type: Literal["remote-reader"] = "remote-reader"
    host: str
    username: str
    path: Path
    wsl: bool = Field(default=False)
    protocol: str = Field(default="rsync")

    @classmethod
    def from_str(
        cls,
        s: str,
        /,
        wsl: bool = False,
        protocol: str = "rsync",
        output_model_type: str | None = None,
    ) -> "RemoteReaderMethod":
        username, rest = s.split("@")
        host, path = rest.split(":")
        return cls(
            username=username,
            host=host,
            path=Path(path),
            wsl=wsl,
            protocol=protocol,
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
            self.run_command(dst_path)
            model = store.run(dst_path, plugin=self.plugin)
            model.title = self.path.name
        model.workflow = self.construct_workflow()
        return model

    def run_command(self, dst_path: Path, stdout=None):
        """Run scp/rsync command to move the file from remote to local `dst_path`."""
        args = remote_to_local(self.protocol, self.to_str(), dst_path, is_wsl=self.wsl)
        subprocess.run(args, stdout=stdout)
        return None

    def _to_command_args(self, src: str, dst: str) -> list[str]:
        if self.protocol == "rsync":
            return ["rsync", "-a", "--progress", src, dst]
        elif self.protocol == "scp":
            return ["scp", src, dst]
        raise ValueError(
            f"Unsupported method {self.protocol!r} (must be 'rsync' or 'scp')"
        )
