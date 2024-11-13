from __future__ import annotations
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW
from himena.builtins.qt.widgets.table import QDefaultTableWidget
from himena.types import WidgetDataModel
from himena.consts import StandardTypes

_EDIT_DISABLED = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
_EDIT_ENABLED = (
    QtW.QAbstractItemView.EditTrigger.DoubleClicked
    | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
)


class QTableStack(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self._edit_trigger = _EDIT_ENABLED

    def update_model(self, model: WidgetDataModel[dict[str, list[list[str]]]]):
        self.clear()
        for sheet_name, table in model.value.items():
            table_widget = QDefaultTableWidget()
            table_widget.update_model(
                WidgetDataModel(value=table, type=StandardTypes.TABLE)
            )
            self.addTab(table_widget, sheet_name)
        return None

    def to_model(self) -> WidgetDataModel[dict[str, list[list[str]]]]:
        return WidgetDataModel(
            value={
                self.tabText(i): self.widget(i).to_model().value
                for i in range(self.count())
            },
            type=self.model_type(),
            extension_default=".xlsx",
        )

    def model_type(self):
        return StandardTypes.EXCEL

    def is_modified(self) -> bool:
        return any(self.widget(i).is_modified() for i in range(self.count()))

    def set_modified(self, value: bool) -> None:
        for i in range(self.count()):
            self.widget(i).set_modified(value)

    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    def is_editable(self) -> bool:
        return self._edit_trigger == _EDIT_ENABLED

    def set_editable(self, value: bool) -> None:
        self._edit_trigger = _EDIT_ENABLED if value else _EDIT_DISABLED
        for i in range(self.count()):
            self.widget(i).set_editable(value)

    if TYPE_CHECKING:

        def widget(self, index: int) -> QDefaultTableWidget: ...
