from __future__ import annotations

from pathlib import Path
import logging
from typing import TYPE_CHECKING, Mapping, Sequence
import warnings
from qtpy import QtWidgets as QtW, QtCore
from himena.plugins._checker import validate_protocol
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena._descriptors import LocalReaderMethod
from himena._utils import unwrap_lazy_model
from himena_builtins.qt.widgets._splitter import QSplitterHandle

if TYPE_CHECKING:
    from himena.widgets import MainWindow

_LOGGER = logging.getLogger(__name__)
_WIDGET_ROLE = QtCore.Qt.ItemDataRole.UserRole
_MODEL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1


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
        self._get_btn = QtW.QPushButton("Get")
        self._get_btn.setToolTip(
            "Get the current item from this list and re-open in the main window, just "
            "like the get-item method of a list."
        )
        self._get_btn.clicked.connect(self._get_current)
        self._delete_btn = QtW.QPushButton("Del")
        self._delete_btn.setToolTip(
            "Delete the current item from this list. This action does not delete the "
            "original file."
        )
        self._delete_btn.clicked.connect(self._delete_current)
        btn_layout = QtW.QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addWidget(self._get_btn)
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
        self._model_list.currentItemChanged.connect(self._current_changed)
        self._last_index: int | None = None
        self.setSizes([160, 320])

        self._control_widget = QtW.QStackedWidget()
        self._is_editable = True

    def createHandle(self):
        return QSplitterHandle(self, "left")

    @validate_protocol
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
            if model.type == StandardType.LAZY:
                item = self._make_lazy_item(name, model)
            else:
                item = self._make_eager_item(name, model)
            self._model_list.addItem(item)

    def _make_lazy_item(self, name: str, model: WidgetDataModel):
        """Make a list item that will convert a file into a widget when needed."""
        item = QtW.QListWidgetItem(name)
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        if isinstance(model.value, (str, Path, LocalReaderMethod)):
            item.setData(_MODEL_ROLE, model)
            item.setData(_WIDGET_ROLE, None)
        else:
            warnings.warn(
                "Lazy model should have Path or LocalReaderMethod as its value.",
                UserWarning,
                stacklevel=2,
            )
        return item

    def _make_eager_item(self, name: str, model: WidgetDataModel):
        """Make a list item that will immediately converted intoa widget."""
        item = QtW.QListWidgetItem(name)
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setData(_MODEL_ROLE, None)
        widget = self._model_to_widget(model)
        self._add_widget(item, widget)
        return item

    def _model_to_widget(self, model: WidgetDataModel) -> QtW.QWidget:
        return self._ui._pick_widget(model)

    def _add_widget(self, item: QtW.QListWidgetItem, widget: QtW.QWidget):
        self._widget_stack.addWidget(widget)
        if hasattr(widget, "control_widget"):
            self._control_widget.addWidget(widget.control_widget())
        else:
            self._control_widget.addWidget(QtW.QWidget())  # empty
        item.setData(_WIDGET_ROLE, widget)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        models: list[WidgetDataModel] = []
        for ith in range(self._model_list.count()):
            item = self._model_list.item(ith)
            model = item.data(_MODEL_ROLE)
            if model is None:  # not a lazy item
                model = item.data(_WIDGET_ROLE).to_model()
            else:
                model = self._exec_lazy_loading(model)
            name = item.text()
            model.title = name
            models.append(model)
        return WidgetDataModel(value=models, type=StandardType.MODELS)

    @validate_protocol
    def model_type(self) -> StandardType:
        return StandardType.MODELS

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 480, 380

    @validate_protocol
    def control_widget(self):
        return self._control_widget

    @validate_protocol
    def is_editable(self):
        return self._is_editable

    @validate_protocol
    def set_editable(self, editable: bool):
        self._is_editable = editable
        self._model_list.setEditTriggers(
            QtW.QAbstractItemView.EditTrigger.DoubleClicked
            | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
            if editable
            else QtW.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._delete_btn.setEnabled(editable)

    @validate_protocol
    def merge_model(self, model: WidgetDataModel):
        item = self._make_eager_item(model.title, model)
        self._model_list.addItem(item)

    def _update_current_index(self):
        row = self._model_list.currentRow()
        item = self._model_list.item(row)
        widget = item.data(_WIDGET_ROLE)
        if widget is None:
            model = item.data(_MODEL_ROLE)
            if model is None:
                widget = QtW.QLabel("Not Available")
            else:
                model = self._exec_lazy_loading(model)
                widget = self._model_to_widget(model)
            self._add_widget(item, widget)
        idx = self._widget_stack.indexOf(widget)
        self._widget_stack.setCurrentIndex(idx)
        self._control_widget.setCurrentIndex(idx)
        self._control_widget.currentWidget().setVisible(True)
        self._control_widget.setVisible(True)

    def _current_changed(self):
        if self._last_index is not None:
            item = self._model_list.item(self._last_index)
            if (
                (model := item.data(_MODEL_ROLE))
                and (widget := item.data(_WIDGET_ROLE))
                and not _is_modified(widget)
            ):
                item.setData(_WIDGET_ROLE, None)
                item.setData(_MODEL_ROLE, model)
                assert isinstance(widget, QtW.QWidget)
                stack_idx = self._widget_stack.indexOf(widget)
                self._widget_stack.removeWidget(widget)
                widget.deleteLater()
                ctrl_widget = self._control_widget.widget(stack_idx)
                if ctrl_widget:
                    self._control_widget.removeWidget(ctrl_widget)
                    ctrl_widget.deleteLater()

        self._update_current_index()
        self._last_index = self._model_list.currentRow()

    def _exec_lazy_loading(self, model: WidgetDataModel) -> WidgetDataModel:
        """Run the pending lazy loading."""
        _LOGGER.info("Lazy loading of: %r", model)
        val = model.value
        model = unwrap_lazy_model(model)
        # determine the title
        if isinstance(val, LocalReaderMethod):
            val = val.path
        if isinstance(val, (str, Path)):
            model.title = Path(val).name
        else:
            model.title = "File Group"
        return model

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

    def _get_current(self):
        if widget := self._widget_stack.currentWidget():
            model = widget.to_model()
            assert isinstance(model, WidgetDataModel)
            model.title = self._model_list.currentItem().text()
            self._ui.add_data_model(model)

    def _delete_current(self):
        ith = self._model_list.currentRow()
        widget = self._widget_stack.widget(ith)
        if _is_modified(widget):
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


def _is_modified(widget: QtW.QWidget):
    return hasattr(widget, "is_modified") and widget.is_modified()
