from himena.testing import WidgetTester, table
from himena_builtins.qt.widgets.table import QSpreadsheet

def test_table_view_accepts_table_like():
    table.test_accepts_table_like(_get_tester())

def test_table_view_current_position():
    table.test_current_position(_get_tester())

def test_table_view_selections():
    table.test_selections(_get_tester())

def _get_tester():
    return WidgetTester(QSpreadsheet())
