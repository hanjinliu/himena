from himena.plugins import when_reader_used
from himena import StandardType

def test_table_hints(make_himena_ui):
    himena_ui = make_himena_ui("mock")
    execs = list(when_reader_used(StandardType.TABLE).iter_executables(himena_ui, "xxx.csv"))
    command_ids = [exe.command_id for exe in execs]
    assert "builtins:table-to-dataframe" in command_ids
