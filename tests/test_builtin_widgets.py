from himena.qt.magicgui import get_type_map

from himena.standards.model_meta import TableMeta
from himena.widgets import MainWindow, SubWindow
from himena.utils.table_selection import SelectionType, table_selection_gui_option
from himena_builtins.qt.history._widget import QCommandHistory

def test_command_added(himena_ui: MainWindow):
    history_widget = QCommandHistory(himena_ui)
    assert history_widget._command_list.model().rowCount() == 0
    himena_ui.exec_action("new-tab")
    assert history_widget._command_list.model().rowCount() == 1
    himena_ui.exec_action("builtins:new-text")

def test_table_selection(himena_ui: MainWindow):
    from himena.qt.magicgui import SelectionEdit

    typemap = get_type_map()

    win = himena_ui.add_object(
        [[1, 2], [3, 4], [3, 2]], metadata=TableMeta(selections=[((0, 3), (1, 2))])
    )

    @typemap.magicgui(x=table_selection_gui_option(win))
    def f(x: SelectionType):
        pass

    assert isinstance(f.x, SelectionEdit)
    f.x._read_btn.clicked()
    assert f.x.value == ((0, 3), (1, 2))
    assert f.x._line_edit.value == "0:3, 1:2"

    @typemap.magicgui(
        table={"value": win},
        x=table_selection_gui_option("table"),
    )
    def f(table: SubWindow, x: SelectionType):
        pass


    f.x._read_btn.clicked()
    assert f.x.value == ((0, 3), (1, 2))
    assert f.x._line_edit.value == "0:3, 1:2"
