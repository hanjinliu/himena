from himena import MainWindow
from pathlib import Path

from himena.consts import StandardType

def test_compute_workflow(himena_ui: MainWindow, sample_dir: Path, tmpdir):
    tmpdir = Path(tmpdir)
    himena_ui.read_file(sample_dir / "table.csv")
    himena_ui.exec_action("builtins:table-to-text", with_params={})
    model = himena_ui.current_model
    assert model
    assert len(model.workflow) == 2
    model_recalc = model.workflow.compute(process_output=False)
    assert model_recalc.value == model.value
    himena_ui.exec_action("show-workflow-graph")
    assert himena_ui.current_model.type == StandardType.WORKFLOW
    response = lambda: tmpdir / "output.workflow.json"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response)
    himena_ui.exec_action("save-as")
    himena_ui.exec_action("open-file")

def test_compute_workflow_binary(himena_ui: MainWindow, tmpdir):
    tmpdir = Path(tmpdir)
    tab = himena_ui.add_tab()
    himena_ui.exec_action("builtins:constant-array", with_params={"shape": (3, 3), "value": 1})
    himena_ui.exec_action("builtins:constant-array", with_params={"shape": (3, 3), "value": 2})
    himena_ui.exec_action("builtins:simple-calculation", with_params={"expr": "x / 2 + 1"})
    himena_ui.exec_action(
        "builtins:binary-operation",
        with_params={
            "x": tab[0].to_model(),
            "operation": "add",
            "y": tab[2].to_model(),
        }
    )
    wf = tab[3].to_model().workflow
    himena_ui.exec_action("show-workflow-graph")
    response = lambda: tmpdir / "output.workflow.json"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response)
    himena_ui.exec_action("save-as")
    himena_ui.exec_action("open-file")
    model = wf.compute(process_output=False)
    assert model.value.tolist() == tab[3].to_model().value.tolist()
