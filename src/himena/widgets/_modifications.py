from __future__ import annotations

from dataclasses import dataclass, field
import timeit
from typing import Generic, TypeVar
import warnings
from himena.types import WidgetDataModel
from himena.plugins import AppActionRegistry
from himena.workflow import (
    CommandExecution,
    parse_parameter,
    ProgrammaticMethod,
    UserModification,
)

_T = TypeVar("_T")


@dataclass
class Modifications(Generic[_T]):
    """Class that tracks modifications to a SubWindow."""

    initial_value: _T | None = field(default=None)
    initial_time: float = field(default_factory=timeit.default_timer)
    track_enabled: bool = field(default=False)

    def update_workflow(self, model: WidgetDataModel) -> None:
        """Update the workflow with a modification step."""
        if self.initial_value is None or not self.track_enabled:
            return None  # No need to update the workflow
        if isinstance(model.workflow.last(), (UserModification, ProgrammaticMethod)):
            # Already has a untrackable modification, so we don't need to do anything
            return
        _reg = AppActionRegistry.instance()
        if model.type not in _reg._modification_trackers:
            warnings.warn(
                f"Modification tracking not available for {model.type}.",
                UserWarning,
                stacklevel=2,
            )
        else:
            mod_tracker = _reg._modification_trackers[model.type]
            try:
                diff = mod_tracker(self.initial_value, model.value)
            except Exception as e:
                # If the diff fails, warn the user and skip the tracking to avoid crashing
                warnings.warn(
                    f"Modification tracking failed for {model.type}: {e}",
                    UserWarning,
                    stacklevel=2,
                )
                diff = None
        if diff:
            model_param = parse_parameter("model", model)
            model.workflow = model.workflow.with_step(
                CommandExecution(
                    command_id=diff.command_id,
                    contexts=[model_param[0]],
                    parameters=[
                        parse_parameter(name, value)[0]
                        for name, value in diff.with_params.items()
                    ],
                    execution_time=timeit.default_timer() - self.initial_time,
                )
            )
        else:
            model.workflow = model.workflow.with_step(
                UserModification(original=model.workflow.last_id())
            )
