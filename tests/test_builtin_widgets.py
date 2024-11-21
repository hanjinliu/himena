from himena.widgets import MainWindow
from himena.builtins.qt.history._widget import QCommandHistory

def test_command_added(ui: MainWindow):
    history_widget = QCommandHistory(ui)
    assert history_widget._command_list.model().rowCount() == 0
    ui.exec_action("new-tab")
    assert history_widget._command_list.model().rowCount() == 1
    ui.exec_action("builtins:new-text")
