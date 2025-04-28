from typing import Callable

from himena import MainWindow
from pathlib import Path

from himena.consts import StandardType
from himena.testing import file_dialog_response
from himena.workflow import LocalReaderMethod, CommandExecution

def test_compute_workflow(make_himena_ui: Callable[..., MainWindow], sample_dir: Path, tmpdir):
    himena_ui = make_himena_ui("mock")
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
    with file_dialog_response(himena_ui, tmpdir / "output.workflow.json"):
        himena_ui.exec_action("save-as")
        himena_ui.exec_action("open-file")

def test_compute_workflow_binary(make_himena_ui: Callable[..., MainWindow], tmpdir):
    himena_ui = make_himena_ui("mock")
    tmpdir = Path(tmpdir)
    tab = himena_ui.add_tab()
    himena_ui.exec_action("builtins:constant-array", with_params={"shape": (3, 3), "value": 1})
    himena_ui.exec_action("builtins:constant-array", with_params={"shape": (3, 3), "value": 2})
    himena_ui.exec_action("builtins:array:simple-calculation", with_params={"expr": "x / 2 + 1"})
    himena_ui.exec_action(
        "builtins:array:binary-operation",
        with_params={
            "x": tab[0].to_model(),
            "operation": "add",
            "y": tab[2].to_model(),
        }
    )
    wf = tab[3].to_model().workflow
    himena_ui.exec_action("show-workflow-graph")
    with file_dialog_response(himena_ui, tmpdir / "output.workflow.json"):
        himena_ui.exec_action("save-as")
        himena_ui.exec_action("open-file")
        model = wf.compute(process_output=False)
        assert model.value.tolist() == tab[3].to_model().value.tolist()

def test_workflow_inherited(make_himena_ui: Callable[..., MainWindow], sample_dir: Path):
    himena_ui = make_himena_ui("mock")
    himena_ui.read_file(sample_dir / "table.csv")
    win0 = himena_ui.current_window
    himena_ui.exec_action("builtins:table-to-text", with_params={})
    win1 = himena_ui.current_window
    himena_ui.exec_action("builtins:table-to-dataframe", window_context=win0)
    win2 = himena_ui.current_window
    himena_ui.exec_action("builtins:dataframe-to-table")
    win3 = himena_ui.current_window

    assert len(win0.to_model().workflow) == 1
    assert isinstance(win0.to_model().workflow.steps[0], LocalReaderMethod)
    assert len(win1.to_model().workflow) == 2
    assert isinstance(win1.to_model().workflow.steps[0], LocalReaderMethod)
    assert isinstance(win1.to_model().workflow.steps[1], CommandExecution)
    assert len(win2.to_model().workflow) == 2
    assert isinstance(win2.to_model().workflow.steps[0], LocalReaderMethod)
    assert isinstance(win2.to_model().workflow.steps[1], CommandExecution)
    assert len(win3.to_model().workflow) == 3
    assert isinstance(win3.to_model().workflow.steps[0], LocalReaderMethod)
    assert isinstance(win3.to_model().workflow.steps[1], CommandExecution)
    assert isinstance(win3.to_model().workflow.steps[2], CommandExecution)

def test_workflow_parametric(make_himena_ui: Callable[..., MainWindow], sample_dir: Path):
    from himena.workflow import as_function

    himena_ui = make_himena_ui("mock")
    himena_ui.read_file(sample_dir / "table.csv")
    win_first = himena_ui.current_window
    himena_ui.exec_action("builtins:table-to-dataframe")
    himena_ui.exec_action("builtins:plot:line", with_params={
        "x": ((0, 5), (0, 1)),
        "y": ((0, 5), (1, 2)),
    })
    model = himena_ui.current_model
    wf_old = model.workflow
    assert len(wf_old.steps) > 2
    wf = wf_old.replace_with_input(wf_old.steps[0].id)
    assert len(wf.steps) == len(wf_old.steps)
    inner_fn = as_function(wf)(himena_ui)
    inner_fn(arg0=win_first.to_model())

def test_list_of_subwindows_input(make_himena_ui: Callable[..., MainWindow]):
    himena_ui = make_himena_ui("qt")
    himena_ui.exec_action("builtins:constant-array", with_params={"interpret_as_image": True, "shape": (3, 3), "value": 1})
    win0 = himena_ui.current_window
    himena_ui.exec_action("builtins:constant-array", with_params={"interpret_as_image": True, "shape": (3, 3), "value": 2})
    win1 = himena_ui.current_window
    himena_ui.exec_action("builtins:image:stack-images", with_params={"images": [win0, win1], "axis_name": "p"})
    win2 = himena_ui.current_window
    # TODO: fix this in the future
    # win2.to_model().workflow.compute(True)
