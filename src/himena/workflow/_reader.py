import tempfile
from typing import Iterator, Literal, Any, TYPE_CHECKING
from pathlib import Path
import subprocess

from pydantic import Field
from himena.exceptions import NotExecutable
from himena.utils.misc import PluginInfo
from himena.utils.cli import remote_to_local, wsl_to_local
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
        raise NotExecutable("Data was added programmatically, thus cannot be executed.")


class UserInput(NoParentWorkflow):
    """Describes that one will be provided as a runtime user input."""

    type: Literal["input"] = "input"
    label: str = Field(default="")
    doc: str = Field(default="")
    how: Literal["file", "model"] = "model"

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        raise NotExecutable("No user input bound to this workflow step.")


class RuntimeInputBound(UserInput):
    bound_value: Any

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        return self.bound_value


class ReaderMethod(NoParentWorkflow):
    """Describes that one was read from a file."""

    plugin: str | None = Field(default=None)
    metadata_override: Any | None = Field(default=None)

    def run(self) -> "WidgetDataModel":
        raise NotImplementedError

    def _run_store(self, path: Path | list[Path]) -> "WidgetDataModel[Any]":
        from himena._providers import ReaderStore

        store = ReaderStore.instance()
        return store.run(path, plugin=self.plugin)


class LocalReaderMethod(ReaderMethod):
    """Describes that one was read from a local source file."""

    type: Literal["local-reader"] = "local-reader"
    path: Path | list[Path]

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel[Any]":
        out = self.run()
        if main := wf._mock_main_window:
            win = main.add_data_model(out)
            win._identifier = self.id
        return out

    def run(self) -> "WidgetDataModel[Any]":
        """Get model by importing the reader plugin and actually read the file(s)."""
        from himena.types import WidgetDataModel

        model = self._run_store(self.path)
        if not isinstance(model, WidgetDataModel):
            raise ValueError(f"Expected to return a WidgetDataModel but got {model}")
        if len(model.workflow) == 0:
            model = model._with_source(
                source=self.path,
                plugin=PluginInfo.from_str(self.plugin) if self.plugin else None,
                id=self.id,
            )
        if self.metadata_override is not None:
            model.metadata = self.metadata_override
        return model


class RemoteReaderMethod(ReaderMethod):
    """Describes that one was read from a remote source file."""

    type: Literal["remote-reader"] = "remote-reader"
    host: str
    username: str
    path: Path
    port: int = Field(default=22)
    wsl: bool = Field(default=False)
    protocol: str = Field(default="rsync")
    force_directory: bool = Field(default=False)

    @classmethod
    def from_str(
        cls,
        s: str,
        /,
        wsl: bool = False,
        protocol: str = "rsync",
        output_model_type: str | None = None,
        force_directory: bool = False,
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
            force_directory=force_directory,
        )

    def to_str(self) -> str:
        """Return the remote file path representation."""
        return f"{self.username}@{self.host}:{self.path.as_posix()}"

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        out = self.run()
        if main := wf._mock_main_window:
            win = main.add_data_model(out)
            win._identifier = self.id
        return out

    def run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst_path = Path(tmpdir).joinpath(self.path.name)
            self.run_command(dst_path)
            model = self._run_store(dst_path)
            model.title = self.path.name
        model.workflow = self.construct_workflow()
        return model

    def run_command(self, dst_path: Path, stdout=None):
        """Run scp/rsync command to move the file from remote to local `dst_path`."""
        args = remote_to_local(
            self.protocol,
            self.to_str(),
            dst_path,
            is_wsl=self.wsl,
            is_dir=self.force_directory,
            port=self.port,
        )
        result = subprocess.run(args, stdout=stdout)
        if result.returncode != 0:
            raise ValueError(f"Failed to run command {args}: {result!r}")


class WslReaderMethod(ReaderMethod):
    """Describes that one was read from a WSL source file."""

    type: Literal["wsl-reader"] = "wsl-reader"
    path: Path
    force_directory: bool = Field(default=False)

    def run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst_path = Path(tmpdir).joinpath(self.path.name)
            self.run_command(dst_path)
            model = self._run_store(dst_path)
            model.title = self.path.name
        model.workflow = self.construct_workflow()
        return model

    def run_command(self, dst_path: Path, stdout=None):
        """Run cp command to move the file from wsl to local `dst_path`."""

        args = wsl_to_local(self.path, dst_path, is_dir=self.force_directory)
        result = subprocess.run(args, stdout=stdout)
        if result.returncode != 0:
            raise ValueError(f"Failed to run command {args}: {result!r}")
