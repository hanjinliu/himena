from pathlib import Path

import pandas as pd
from qtpy import QtWidgets as QtW
from royalapp import (
    new_window,
    register_reader_provider,
    register_writer_provider,
    WidgetDataModel,
)
from royalapp.qt import register_frontend_widget

PANDAS_TABLE_TYPE = object()

# `@register_frontend_widget` is a decorator that registers a widget class as a frontend
# widget for the given file type. The class must have an `from_model` method to convert
# data model to its instance. By further providing `to_model` method, the widget can
# be converted back to data model.
@register_frontend_widget(PANDAS_TABLE_TYPE)
class DataFrameWidget(QtW.QTableWidget):
    def __init__(self, model: WidgetDataModel[pd.DataFrame]):
        df = model.value
        super().__init__(df.shape[0], df.shape[1])
        # set table items
        for i, col in enumerate(df.columns):
            self.setHorizontalHeaderItem(i, QtW.QTableWidgetItem(col))
            for j, value in enumerate(df[col]):
                self.setItem(j, i, QtW.QTableWidgetItem(str(value)))
        for j, index in enumerate(df.index):
            self.setVerticalHeaderItem(j, QtW.QTableWidgetItem(str(index)))
        self._model = model

    @classmethod
    def from_model(cls, model: WidgetDataModel[pd.DataFrame]):
        self = cls(model)
        return self

    def to_model(self) -> WidgetDataModel:
        return self._model

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
