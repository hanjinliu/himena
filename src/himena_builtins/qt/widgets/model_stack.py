from __future__ import annotations

from pathlib import Path
import logging
from typing import TYPE_CHECKING, Any, Mapping, Sequence
import warnings
import weakref
from magicgui import widgets as mgw
from qtpy import QtWidgets as QtW, QtCore, QtGui
from himena.plugins import validate_protocol, _checker
from himena.types import DragDataModel, WidgetDataModel
from himena.consts import StandardType
from himena._descriptors import LocalReaderMethod
from himena._utils import unwrap_lazy_model
from himena_builtins.qt.widgets._splitter import QSplitterHandle
from himena.qt import drag_model

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from himena.style import Theme

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

        self._model_list = QModelListWidget(self)
        left.setFixedWidth(160)
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

    def _model_to_widget(self, model: WidgetDataModel) -> Any:
        # this may return the interface, not the QWidget!
        return self._ui._pick_widget(model)

    def _add_widget(self, item: QtW.QListWidgetItem, widget: Any):
        interf, native_widget = _split_widget_and_interface(widget)
        self._widget_stack.addWidget(native_widget)

        if hasattr(interf, "control_widget"):
            self._control_widget.addWidget(interf.control_widget())
        else:
            self._control_widget.addWidget(QtW.QWidget())  # empty
        item.setData(_WIDGET_ROLE, interf)
        _checker.call_window_added_callback(interf)
        _checker.call_theme_changed_callback(interf, self._ui.theme)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        models: list[WidgetDataModel] = []
        for ith in range(self._model_list.count()):
            item = self._model_list.item(ith)
            model = self._model_list.model_at_index(ith)
            if model is None:
                continue  # this should not happen
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
        if model.type == StandardType.LAZY:
            item = self._make_lazy_item(model.title, model)
        else:
            item = self._make_eager_item(model.title, model)
        self._model_list.addItem(item)

    # TODO: Implement the following methods
    # @validate_protocol
    # def window_resized_callback(self, size_old: Size, size_new: Size):
    #     widget = self._widget_stack.currentWidget()
    #     _checker.call_window_resized_callback(widget, ...)

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        if widget := self._widget_stack.currentWidget():
            _checker.call_theme_changed_callback(widget, theme)

    def _update_current_index(self):
        row = self._model_list.currentRow()
        item = self._model_list.item(row)
        widget = item.data(_WIDGET_ROLE)
        if widget is None:
            model = item.data(_MODEL_ROLE)
            if model is None:
                widget = QtW.QLabel("Not Available")
            else:
                model = _exec_lazy_loading(model)
                widget = self._model_to_widget(model)
            self._add_widget(item, widget)
        _, native_widget = _split_widget_and_interface(widget)
        idx = self._widget_stack.indexOf(native_widget)
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
                _, native_widget = _split_widget_and_interface(widget)
                assert isinstance(native_widget, QtW.QWidget)
                stack_idx = self._widget_stack.indexOf(native_widget)
                self._widget_stack.removeWidget(native_widget)
                native_widget.deleteLater()
                ctrl_widget = self._control_widget.widget(stack_idx)
                if ctrl_widget:
                    self._control_widget.removeWidget(ctrl_widget)
                    ctrl_widget.deleteLater()

        self._update_current_index()
        self._last_index = self._model_list.currentRow()

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
        """Clone the current model and add it to the main window."""
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


def _is_drag_mouse_event(e: QtGui.QMouseEvent):
    return (
        e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        and e.buttons() & QtCore.Qt.MouseButton.LeftButton
    ) or e.buttons() & QtCore.Qt.MouseButton.MiddleButton


class QModelListWidget(QtW.QListWidget):
    def __init__(self, parent: QModelStack):
        super().__init__(parent)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(
            QtW.QAbstractItemView.EditTrigger.DoubleClicked
            | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._is_dragging = False
        self._model_stack_ref = weakref.ref(parent)

    def mousePressEvent(self, e):
        if _is_drag_mouse_event(e):
            return None
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._is_dragging:
            return super().mouseMoveEvent(e)
        self._is_dragging = True
        if _is_drag_mouse_event(e):
            items = self.selectedItems()
            if len(items) == 0:
                return None
            if len(items) == 1:

                def _getter():
                    return self.model_for_item(items[0])

                if item_model := items[0].data(_MODEL_ROLE):
                    model_type = item_model.type
                else:
                    model_type = None
            else:

                def _getter():
                    return WidgetDataModel(
                        value=[self.model_for_item(item) for item in items],
                        type=StandardType.MODELS,
                        title="Models",
                    )

                model_type = StandardType.MODELS
            model = DragDataModel(getter=_getter, type=model_type)
            drag_model(
                model, desc=f"{len(items)} items", source=self._model_stack_ref()
            )
        else:
            super().mouseMoveEvent(e)
        return None

    def mouseReleaseEvent(self, e):
        self._is_dragging = False
        if _is_drag_mouse_event(e):
            return super().mousePressEvent(e)
        return super().mouseReleaseEvent(e)

    def getter_for_item(self, item: QtW.QListWidgetItem):
        return lambda: self.model_for_item(item)

    def model_for_item(self, item: QtW.QListWidgetItem):
        model = item.data(_MODEL_ROLE)
        if model is None:  # not a lazy item
            model = item.data(_WIDGET_ROLE).to_model()
        else:
            model = _exec_lazy_loading(model)
        return model

    def model_at_index(self, row: int) -> WidgetDataModel | None:
        item = self.item(row)
        if item is None:
            return None
        return self.model_for_item(item)


def _exec_lazy_loading(model: WidgetDataModel) -> WidgetDataModel:
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


def _split_widget_and_interface(widget) -> tuple[Any, QtW.QWidget]:
    if hasattr(widget, "native_widget"):
        interf = widget
        native_widget = interf.native_widget()
    elif isinstance(widget, mgw.Widget):
        interf = widget
        native_widget = interf.native
    elif isinstance(widget, QtW.QWidget):
        interf = native_widget = widget
    else:
        raise TypeError(f"Expected a widget or an interface, got {type(widget)}")
    return interf, native_widget
