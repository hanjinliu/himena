from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Sequence
from qtpy import QtWidgets as QtW, QtCore
from himena.plugins._checker import protocol_override
from himena.types import WidgetDataModel
from himena.consts import StandardType

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QModelStack(QtW.QSplitter):
    """A widget that contains a list of models."""

    __himena_widget_id__ = "builtins:QModelStack"
    __himena_display_name__ = "Built-in Model Stack"

    def __init__(self, ui: MainWindow):
        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self._ui = ui
        left = QtW.QWidget()
        layout = QtW.QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        self._save_btn = QtW.QPushButton("Save")
        self._save_btn.setToolTip("Save the current model to a file.")
        self._save_btn.clicked.connect(self._save_current)
        self._pop_btn = QtW.QPushButton("Pop")
        self._pop_btn.setToolTip(
            "Pop the current model from this stack and re-open in the main window."
        )
        self._pop_btn.clicked.connect(self._pop_current)
        self._delete_btn = QtW.QPushButton("Del")
        self._delete_btn.setToolTip("Delete the current model from this stack.")
        self._delete_btn.clicked.connect(self._delete_current)
        btn_layout = QtW.QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addWidget(self._pop_btn)
        btn_layout.addWidget(self._delete_btn)

        self._model_list = QtW.QListWidget()
        self._model_list.setSelectionMode(
            QtW.QAbstractItemView.SelectionMode.SingleSelection
        )
        left.setFixedWidth(160)
        self._model_list.setEditTriggers(
            QtW.QAbstractItemView.EditTrigger.DoubleClicked
            | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._widget_stack = QtW.QStackedWidget()
        layout.addWidget(self._model_list)
        layout.addLayout(btn_layout)

        self.addWidget(left)
        self.addWidget(self._widget_stack)
        self._model_list.itemClicked.connect(self._update_current_index)
        self.setSizes([160, 320])

        self._control_widget = QtW.QStackedWidget()

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        value = model.value
        name_model_list: list[tuple[str, WidgetDataModel]] = []
        if isinstance(value, Sequence):
            for each in value:
                if isinstance(each, WidgetDataModel):
                    name_model_list.append((each.title, each))
                elif (
                    isinstance(each, Sequence)
                    and len(each) == 2
                    and isinstance(each[1], WidgetDataModel)
                ):
                    name_model_list.append((str(each[0]), each[1]))
                else:
                    raise TypeError(
                        f"Expected a WidgetDataModel or (name, WidgetDataModel), got "
                        f"{type(each)}"
                    )
        elif isinstance(value, Mapping):
            for key, each in value.items():
                if not isinstance(each, WidgetDataModel):
                    raise TypeError(
                        f"Expected WidgetDataModel as the values, got {type(each)}"
                    )
                name_model_list.append((key, each))
        else:
            raise TypeError(f"Expected Sequence or Mapping, got {type(value)}")

        # clear the stack
        while w := self._widget_stack.currentWidget():
            self._widget_stack.removeWidget(w)

        # add new widgets one by one
        self._model_list.clear()
        for name, model in name_model_list:
            widget = self._model_to_widget(model)
            self._add_widget(name, widget)

        if len(name_model_list) > 0:
            self._model_list.setCurrentRow(0)

    def _model_to_widget(self, model: WidgetDataModel) -> QtW.QWidget:
        widget_class = self._ui._pick_widget_class(model)
        try:
            widget = widget_class(self._ui)
        except TypeError:
            widget = widget_class()
        widget.update_model(model)
        return widget

    def _add_widget(self, name: str, widget: QtW.QWidget):
        self._model_list.addItem(name)
        self._widget_stack.addWidget(widget)
        if hasattr(widget, "control_widget"):
            self._control_widget.addWidget(widget.control_widget())
        else:
            self._control_widget.addWidget(QtW.QWidget())  # empty

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        models: list[WidgetDataModel] = []
        for ith in range(self._widget_stack.count()):
            widget = self._widget_stack.widget(ith)
            name = self._model_list.item(ith).text()
            model = widget.to_model()
            model.title = name
            models.append(model)
        return WidgetDataModel(value=models, type=StandardType.MODELS)

    @protocol_override
    def model_type(self) -> StandardType:
        return StandardType.MODELS

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 480, 380

    @protocol_override
    def control_widget(self):
        return self._control_widget

    @protocol_override
    def merge_model(self, model: WidgetDataModel):
        widget = self._model_to_widget(model)
        self._add_widget(model.title, widget)

    def _update_current_index(self):
        row = self._model_list.currentRow()
        self._widget_stack.setCurrentIndex(row)
        self._control_widget.setCurrentIndex(row)

    def _save_current(self):
        if widget := self._widget_stack.currentWidget():
            model = widget.to_model()
            assert isinstance(model, WidgetDataModel)
            return self._ui.exec_file_dialog(
                "w",
                extension_default=model.extension_default,
                allowed_extensions=model.extensions,
                caption="Save model to ...",
            )
        return False

    def _pop_current(self):
        if widget := self._widget_stack.currentWidget():
            model = widget.to_model()
            assert isinstance(model, WidgetDataModel)
            model.title = self._model_list.currentItem().text()
            self._ui.add_data_model(model)
            self._delete_widget(self._model_list.currentRow())

    def _delete_current(self):
        ith = self._model_list.currentRow()
        widget = self._widget_stack.widget(ith)
        if hasattr(widget, "is_modified") and widget.is_modified():
            request = self._ui.exec_choose_one_dialog(
                title="Closing window",
                message="The model has been modified. Do you want to save it?",
                choices=["Yes", "No", "Cancel"],
            )
            if request is None or request == "Cancel":
                return None
            elif request == "Yes" and not self._save_current():
                return None
        self._delete_widget(ith)

    def _delete_widget(self, row: int):
        widget = self._widget_stack.widget(row)
        self._widget_stack.removeWidget(widget)
        self._model_list.takeItem(row)
        control = self._control_widget.widget(row)
        self._control_widget.removeWidget(control)
