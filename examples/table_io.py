from pathlib import Path

import pandas as pd
from qtpy import QtWidgets as QtW
from himena import (
    new_window,
    WidgetDataModel,
)
from himena.plugins import register_reader_plugin, register_writer_plugin, register_widget_class

PANDAS_TABLE_TYPE = "table.pandas"

# `@register_widget` is a decorator that registers a widget class as a frontend
# widget for the given file type. The class must have an `update_model` method to update
# the state based on the data model. By further providing `to_model` method, the widget
# can be converted back to data model.
@register_widget_class(PANDAS_TABLE_TYPE)
class DataFrameWidget(QtW.QTableWidget):
    def __init__(self):
        super().__init__()
        self._data_model = None

    def update_model(self, model: WidgetDataModel[pd.DataFrame]):
        df = model.value
        # set table items one by one
        self.setRowCount(df.shape[0])
        self.setColumnCount(df.shape[1])
        for i, col in enumerate(df.columns):
            self.setHorizontalHeaderItem(i, QtW.QTableWidgetItem(col))
            for j, value in enumerate(df[col]):
                self.setItem(j, i, QtW.QTableWidgetItem(str(value)))
        for j, index in enumerate(df.index):
            self.setVerticalHeaderItem(j, QtW.QTableWidgetItem(str(index)))
        self._data_model = model

    def to_model(self) -> WidgetDataModel:
        return self._data_model

# `@register_reader_plugin` is a decorator that registers a function as a reader.
# A `@reader.define_matcher` decorator must follow to define a matcher function.
@register_reader_plugin
def my_reader(file_path: Path):
    if file_path.suffix == ".csv":
        df = pd.read_csv(file_path)
        return WidgetDataModel(value=df, type=PANDAS_TABLE_TYPE)
    elif file_path.suffix == ".xlsx":
        df = pd.read_excel(file_path)
        return WidgetDataModel(value=df, type=PANDAS_TABLE_TYPE)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")

@my_reader.define_matcher
def _(file_path: Path):
    if file_path.suffix in (".csv", ".xlsx"):
        return PANDAS_TABLE_TYPE
    return None

# `@register_writer_plugin` is a decorator that registers a function as a writer.
# A `@writer.define_matcher` decorator must follow to define a matcher function.
@register_writer_plugin
def my_writer(model: WidgetDataModel[pd.DataFrame], path: Path):
    if path.suffix == ".csv":
        model.value.to_csv(path, index=False)
    elif path.suffix == ".xlsx":
        model.value.to_excel(path, index=False)
    raise ValueError(f"Unsupported file type: {path.suffix}")

@my_writer.define_matcher
def _(model: WidgetDataModel[pd.DataFrame], path: Path):
    return path.suffix in (".csv", ".xlsx")

def main():
    ui = new_window()
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    ui.add_object(df, type=PANDAS_TABLE_TYPE, title="test table")
    ui.show(run=True)

if __name__ == "__main__":
    main()
