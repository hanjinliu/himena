from pathlib import Path
from typing import Any, Union
import uuid
from pydantic_compat import BaseModel, Field
from himena.types import WidgetDataModel
from himena.workflow._base import WorkflowStep
from himena.workflow._graph import Workflow
from himena.workflow._reader import ReaderMethod, LocalReaderMethod, SCPReaderMethod


class WorkflowCaller(BaseModel):
    """Callable object that parametrize a part of the workflow."""

    workflow: Workflow
    replacers: list["ReplacerType"] = Field(default_factory=list)
    # NOTE: replacers will use the same UUID for different tasks. This means that the
    # workflow of this model should never be used outside this class.

    def _existing_arg_names(self) -> list[str]:
        return [rp.arg_name for rp in self.replacers]

    def parametrize_reader(
        self,
        step_id: uuid.UUID,
        arg_name: str | None = None,
        *,
        plugin_override: str | None = None,
    ) -> "LocalReaderReplacer":
        plugin = self._norm_plugin(step_id, plugin_override)
        arg_name = self._norm_arg_name(arg_name, stem="path")
        replacer = LocalReaderReplacer(
            step_id=step_id, arg_name=arg_name, plugin=plugin
        )
        self.replacers.append(replacer)
        return replacer

    def parametrize_scp_reader(
        self,
        step_id: uuid.UUID,
        arg_name: str | None = None,
        *,
        plugin_override: str | None = None,
        wsl: bool = False,
    ) -> "SCPReaderReplacer":
        plugin = self._norm_plugin(step_id, plugin_override)
        arg_name = self._norm_arg_name(arg_name, stem="path")
        replacer = SCPReaderReplacer(
            step_id=step_id, arg_name=arg_name, plugin=plugin, wsl=wsl
        )
        self.replacers.append(replacer)
        return replacer

    def _norm_plugin(
        self,
        step_id: uuid.UUID,
        plugin_override: str | None,
    ) -> str:
        if not isinstance(step := self.workflow.step_for_id(step_id), ReaderMethod):
            raise ValueError(f"Step {step_id} is not a reader.")
        plugin_default = step.plugin
        return plugin_override or plugin_default

    def _norm_arg_name(self, arg_name: str | None, stem: str) -> str:
        existing = self._existing_arg_names()
        if arg_name is None:
            idx = 0
            while f"{stem}_{idx}" in existing:
                idx += 1
            arg_name = f"{stem}_{idx}"
        elif arg_name in existing:
            raise ValueError(f"Argument `{arg_name}` already exists")
        return arg_name

    @property
    def __annotations__(self) -> dict[str, Any]:
        annot: dict[str, Any] = {}
        for rp in self.replacers:
            annot[rp.arg_name] = rp.make_annotation()
        annot["return"] = WidgetDataModel
        return annot

    def _run_replaced(self, params: dict[uuid.UUID, dict[str, Any]]):
        steps = self.workflow.steps
        steps_replaced: list[WorkflowStep] = []
        replacer_map = {rp.step_id: rp for rp in self.replacers}
        for step in steps:
            if replacer := replacer_map.get(step.id):
                step = replacer(**params[step.id])
            steps_replaced.append(step)
        wf = Workflow(steps=steps_replaced)
        return wf.compute(process_output=False)


class StepReplacer(BaseModel):
    step_id: uuid.UUID
    arg_name: str

    def create_step(self, *args) -> WorkflowStep:
        raise NotImplementedError

    def make_annotation(self) -> Any:
        raise NotImplementedError


class ReaderReplacer(StepReplacer):
    plugin: str | None = Field(default=None)


class LocalReaderReplacer(ReaderReplacer):
    """Parameter for LocalReaderMethod."""

    def create_step(self, path: Path | list[Path]) -> LocalReaderMethod:
        if isinstance(path, (str, Path)):
            _path = Path(path)
        else:
            _path = [Path(p) for p in path]
        return LocalReaderMethod(path=_path, plugin=self.plugin)

    def make_annotation(self):
        return Path


class SCPReaderReplacer(ReaderReplacer):
    wsl: bool = Field(default=False)

    def create_step(self, path_str: str) -> SCPReaderMethod:
        return SCPReaderMethod.from_str(path_str, wsl=self.wsl)

    def make_annotation(self):
        return str


ReplacerType = Union[LocalReaderReplacer, SCPReaderReplacer]
