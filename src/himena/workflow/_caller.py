from pathlib import Path
from typing import Any, TYPE_CHECKING
import uuid
from himena.workflow._graph import Workflow
from himena.workflow._reader import LocalReaderMethod, UserInput, RuntimInputBound

if TYPE_CHECKING:
    from himena.widgets import MainWindow


def workflow_to_input_fields(wf: Workflow) -> dict[uuid.UUID, Any]:
    from himena.types import WidgetDataModel

    fields = {}
    for step in wf.steps:
        if not isinstance(step, UserInput):
            continue
        option = {"label": step.label, "tooltip": step.doc}
        fields[step.id] = option
        if step.how == "file":
            option["annotation"] = Path
        elif step.how == "model":
            option["annotation"] = WidgetDataModel
        else:
            raise NotImplementedError(f"Unsupported input type: {step.how}")

    return fields


def as_function(wf: Workflow):
    from himena.types import Parametric, WidgetDataModel
    from himena.plugins import configure_gui

    fields = workflow_to_input_fields(wf)
    options = {f"arg{i}": val for i, val in enumerate(fields.values())}
    key_to_id = {f"arg{i}": k for i, k in enumerate(fields.keys())}

    def func(ui: "MainWindow") -> Parametric:
        @configure_gui(**options)
        def inner(**kwargs):
            wf_compute = wf.model_copy()
            wf_out = wf_compute.model_copy()
            for k, v in kwargs.items():
                step_id = key_to_id[k]
                if isinstance(v, Path):
                    wf_compute = wf_compute.replace(
                        step_id, LocalReaderMethod(id=step_id, path=v)
                    )
                    wf_out = wf_out.replace(
                        step_id, LocalReaderMethod(id=step_id, path=v)
                    )
                elif isinstance(v, WidgetDataModel):
                    wf_compute = wf_compute.replace(
                        step_id, RuntimInputBound(id=step_id, bound_value=v)
                    )
                    wf_out = wf_out.replace(step_id, v.workflow)
                else:
                    raise NotImplementedError(f"Unsupported type: {type(v)}")
            out = wf_compute.compute(process_output=True)
            if isinstance(out, WidgetDataModel):
                ui.current_window._update_model_workflow(wf_out)
            return None

        return inner

    return func
