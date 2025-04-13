from qtpy.QtCore import Qt, QPoint
from pytestqt.qtbot import QtBot
from himena import MainWindow, StandardType, WidgetDataModel
from himena.testing import WidgetTester
from himena_builtins.qt.basic import QModelStack

def test_model_stack_widget(himena_ui: MainWindow, qtbot: QtBot):
    win = himena_ui.add_object(
        {"model-0": WidgetDataModel(value="a", type=StandardType.TEXT)},
        type=StandardType.MODELS,
    )
    win.update_model(
        [
            ("model-0", WidgetDataModel(value="a", type=StandardType.TEXT)),
            ("model-1", WidgetDataModel(value="a", type=StandardType.TEXT)),
        ],
        type=StandardType.MODELS,
    )

    assert isinstance(win.widget, QModelStack)
    with WidgetTester(win.widget) as tester:
        tester.widget.show()
        mlist = tester.widget._model_list
        old, new = tester.cycle_model()
        assert len(old.value) == len(new.value)
        assert mlist.count() == 2
        tester.drop_model(
            [
                ("model-10", WidgetDataModel(value="a", type=StandardType.TEXT)),
                ("model-11", WidgetDataModel(value="a", type=StandardType.TEXT)),
            ],
            type=StandardType.MODELS,
        )
        assert mlist.count() == 3  # model list is dropped as a nested list
        row_1 = mlist.model().index(1, 0)
        point_1 = mlist.visualRect(row_1).center()
        qtbot.mouseClick(mlist.viewport(), Qt.MouseButton.LeftButton, pos=point_1)
        assert mlist.currentRow() == 1
        qtbot.mouseMove(mlist.viewport(), point_1 + QPoint(2, 2))

def test_commands(himena_ui: MainWindow):
    win0 = himena_ui.add_object(value="abc", type=StandardType.TEXT)
    win1 = himena_ui.add_object(value=[[1, 2], [3, 2]], type=StandardType.TABLE)
    himena_ui.exec_action("builtins:models:stack-models", with_params={"models": [win1.to_model(), win0.to_model()]})
    win2 = himena_ui.current_window
    assert isinstance(win2.widget, QModelStack)
    assert win2.widget._model_list.count() == 2
    himena_ui.exec_action("builtins:models:sort-model-list", with_params={"sort_by": "title"})
    himena_ui.exec_action("builtins:models:sort-model-list", with_params={"sort_by": "type"})
    himena_ui.exec_action("builtins:models:sort-model-list", with_params={"sort_by": "time"})
    himena_ui.exec_action("builtins:models:filter-model-list", with_params={"model_type": "text"})
    himena_ui.exec_action("builtins:models:filter-model-list", with_params={"title_contains": "X"})
    himena_ui.exec_action("builtins:models:compute-lazy-items")
