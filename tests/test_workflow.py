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

# TODO: use array binary operation
