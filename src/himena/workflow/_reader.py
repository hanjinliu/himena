from contextlib import contextmanager
import tempfile
from typing import Iterator, Literal, Any, TYPE_CHECKING
from pathlib import Path
import subprocess

from pydantic import Field
from himena.consts import StandardType
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


class PathReaderMethod(ReaderMethod):
    """Describes that one was read from a path."""

    path: Path | list[Path]
    force_directory: bool = Field(default=False)

    def run_command(self, dst_path: Path, stdout=None):
        """Run command to move the file from source to local `dst_path`."""
        raise NotImplementedError("No conversion command defined for this method.")

    def to_str(self) -> str:
        """Return the local file path representation."""
        if isinstance(self.path, Path):
            return self.path.as_posix()
        return ";".join(p.as_posix() for p in self.path)

    def _list_dst_filenames(self) -> list[str]:
        if isinstance(self.path, Path):
            filenames = [self.path.name]
        else:
            filenames: list[Path] = []
            for p in self.path:
                filenames.append(p.name)
        return filenames

    @contextmanager
    def run_context(
        self, filenames: list[str] | None = None
    ) -> Iterator[Path | list[Path]]:
        if filenames is None:
            filenames = self._list_dst_filenames()
        with tempfile.TemporaryDirectory() as tmpdir:
            if isinstance(self.path, Path):
                dst_path = Path(tmpdir, filenames[0])
                self.run_command(dst_path)
            else:
                dst_path: list[Path] = []
                for p in filenames:
                    dst_p = Path(tmpdir, p)
                    self.run_command(dst_p)
                    dst_path.append(dst_p)
            yield dst_path

    def run(self) -> "WidgetDataModel":
        from himena._providers import ReaderStore
        from himena.types import WidgetDataModel

        filenames = self._list_dst_filenames()
        store = ReaderStore.instance()
        matched = store.get(Path(filenames[0]), empty_ok=True, min_priority=1)
        if len(filenames) > 1 or matched:
            with self.run_context(filenames) as dst_path:
                model = self._run_store(dst_path)
        else:
            # If the file type is not supported, no need to rsync it.
            model = WidgetDataModel(
                value=self.path,
                type=StandardType.READER_NOT_FOUND,
            )

        model.title = self.path.name
        model.workflow = self.construct_workflow()
        return model


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

    @property
    def force_directory(self) -> bool:
        # just for compatibility with PathReaderMethod
        return isinstance(self.path, Path) and self.path.is_dir()

    @contextmanager
    def run_context(
        self, filenames: list[str] | None = None
    ) -> Iterator[Path | list[Path]]:
        assert filenames is None
        yield self.path

    def to_str(self) -> str:
        """Return the local file path representation."""
        if isinstance(self.path, Path):
            return self.path.as_posix()
        return ";".join(p.as_posix() for p in self.path)

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


class RemoteReaderMethod(PathReaderMethod):
    """Describes that one was read from a remote source file."""

    type: Literal["remote-reader"] = "remote-reader"
    host: str
    username: str
    port: int = Field(default=22)
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
        force_directory: bool = False,
    ) -> "RemoteReaderMethod":
        username, rest = s.split("@")
        host, path = rest.split(":")
        if ";" in path:
            path = [Path(p) for p in path.split(";")]
        else:
            path = Path(path)
        return cls(
            username=username,
            host=host,
            path=path,
            wsl=wsl,
            protocol=protocol,
            output_model_type=output_model_type,
            force_directory=force_directory,
        )

    def to_str(self) -> str:
        """Return the remote file path representation."""
        if isinstance(self.path, Path):
            return f"{self.username}@{self.host}:{self.path.as_posix()}"
        return (
            f"{self.username}@{self.host}:{';'.join(p.as_posix() for p in self.path)}"
        )

    def _get_model_impl(self, wf: "Workflow") -> "WidgetDataModel":
        out = self.run()
        if main := wf._mock_main_window:
            win = main.add_data_model(out)
            win._identifier = self.id
        return out

    def run_command(self, dst_path: Path, stdout=None):
        """Run scp/rsync command to move the file from remote to local `dst_path`."""
        if isinstance(self.path, Path):
            args = remote_to_local(
                self.protocol,
                self.to_str(),
                dst_path,
                is_wsl=self.wsl,
                is_dir=self.force_directory,
                port=self.port,
            )
        else:
            raise ValueError(
                "Cannot run command for multiple paths in RemoteReaderMethod."
            )
        result = subprocess.run(args, stdout=stdout)
        if result.returncode != 0:
            raise ValueError(f"Failed to run command {args}: {result!r}")


class WslReaderMethod(PathReaderMethod):
    """Describes that one was read from a WSL source file."""

    type: Literal["wsl-reader"] = "wsl-reader"

    @classmethod
    def from_str(cls, line: str, force_directory: bool = False) -> "WslReaderMethod":
        """Construct a WslReaderMethod from a string representation."""
        if ";" in line:
            path = [Path(p) for p in line.split(";")]
        else:
            path = Path(line)
        return cls(
            path=path,
            force_directory=force_directory,
        )

    def run_command(self, dst_path: Path, stdout=None):
        """Run cp command to move the file from wsl to local `dst_path`."""

        if isinstance(self.path, Path):
            args = wsl_to_local(
                self.path.as_posix(), dst_path, is_dir=self.force_directory
            )
            result = subprocess.run(args, stdout=stdout)
        else:
            raise ValueError(
                "Cannot run command for multiple paths in WSLReaderMethod."
            )
        if result.returncode != 0:
            raise ValueError(f"Failed to run command {args}: {result!r}")
