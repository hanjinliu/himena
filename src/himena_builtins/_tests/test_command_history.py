from himena import MainWindow
from himena_builtins.qt.history._widget import QCommandHistory

def test_command_added(himena_ui: MainWindow):
    history_widget = QCommandHistory(himena_ui)
    assert history_widget._command_list.model().rowCount() == 0
    himena_ui.exec_action("new-tab")
    assert history_widget._command_list.model().rowCount() == 1

    himena_ui.exec_action("builtins:new-text")
    widget = history_widget._command_list.indexWidget(
        history_widget._command_list.model().index(0, 0)
    )
    widget._make_drag()
    widget._enter_event()
    widget.set_button_visible(True)
    widget.set_button_visible(False)
    widget._emit_copy_clicked()
    widget._emit_run_clicked()
    assert history_widget._command_list._find_index_widget(widget).row() == 0
    history_widget.deleteLater()
