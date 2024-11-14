from pathlib import Path

import pandas as pd
from qtpy import QtWidgets as QtW
from himena import (
    new_window,
    WidgetDataModel,
)
from himena.plugins import register_reader_provider, register_writer_provider
from himena.qt import register_widget

PANDAS_TABLE_TYPE = "table.pandas"

# `@register_widget` is a decorator that registers a widget class as a frontend
# widget for the given file type. The class must have an `update_model` method to update
# the state based on the data model. By further providing `to_model` method, the widget
# can be converted back to data model.
@register_widget(PANDAS_TABLE_TYPE)
class DataFrameWidget(QtW.QTableWidget):
    def __init__(self):
        self._data_model = None

    def update_model(self, model: WidgetDataModel[pd.DataFrame]):
        df = model.value
        # set table items
        self.setRowCount(df.shape[0])
        self.setColumnCount(df.shape[1])
        for i, col in enumerate(df.columns):
            self.setHorizontalHeaderItem(i, QtW.QTableWidgetItem(col))
            for j, value in enumerate(df[col]):
                self.setItem(j, i, QtW.QTableWidgetItem(str(value)))
        for j, index in enumerate(df.index):
            self.setVerticalHeaderItem(j, QtW.QTableWidgetItem(str(index)))

    def to_model(self) -> WidgetDataModel:
        return self._data_model

# `@register_reader_provider` is a decorator that registers a function as one that
# provides a reader for the given file path.
@register_reader_provider
def my_reader_provider(file_path):
    if Path(file_path).suffix == ".csv":
        def _read(file_path):
            df = pd.read_csv(file_path)
            return WidgetDataModel(value=df, type=PANDAS_TABLE_TYPE)
    elif Path(file_path).suffix == ".xlsx":
        def _read(file_path):
            df = pd.read_excel(file_path)
            return WidgetDataModel(value=df, type=PANDAS_TABLE_TYPE)
    else:
        return None
    return _read

# `@register_writer_provider` is a decorator that registers a function as one that
# provides a write for the given data model.
@register_writer_provider
def my_writer_provider(model: WidgetDataModel[pd.DataFrame], path: Path):
    if path.suffix == ".csv":
        def _write(model: WidgetDataModel[pd.DataFrame]):
            model.value.to_csv(path, index=False)
    elif path.suffix == ".xlsx":
        def _write(model: WidgetDataModel[pd.DataFrame]):
            model.value.to_excel(path, index=False)
    else:
        return None
    return _write

def main():
    ui = new_window()
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    ui.add_data(df, type=PANDAS_TABLE_TYPE, title="test table")
    ui.show(run=True)

if __name__ == "__main__":
    main()
