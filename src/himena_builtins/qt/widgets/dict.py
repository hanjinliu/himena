from typing import TYPE_CHECKING, Mapping
import weakref

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.standards.model_meta import DictMeta
from himena.qt._qrename import QTabRenameLineEdit
from himena.qt import drag_command
from himena.types import DropResult, Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.plugins import validate_protocol, register_hidden_function


class QRightClickableTabBar(QtW.QTabBar):
    right_clicked = QtCore.Signal(int)

    def __init__(self, parent: "QDictOfWidgetEdit") -> None:
        super().__init__(parent)
        self._last_right_clicked: int | None = None
        self._is_dragging = False
        self._parent_ref = weakref.ref(parent)

    def mousePressEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == QtCore.Qt.MouseButton.RightButton:
            self._last_right_clicked = self.tabAt(a0.pos())
        return super().mousePressEvent(a0)

    def mouseMoveEvent(self, a0):
        if self._is_dragging:
            return super().mouseMoveEvent(a0)
        if (
            a0.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            and a0.buttons() & QtCore.Qt.MouseButton.LeftButton
        ) or (a0.buttons() & QtCore.Qt.MouseButton.MiddleButton):
            self._is_dragging = True
            if drag := self._make_drag():
                drag.exec()
                return
        return super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == QtCore.Qt.MouseButton.RightButton:
            if self.tabAt(a0.pos()) == self._last_right_clicked:
                self.right_clicked.emit(self._last_right_clicked)
        self._last_right_clicked = None
        self._is_dragging = False
        return super().mouseReleaseEvent(a0)

    def _make_drag(self) -> QtGui.QDrag | None:
        if (qexcel := self._parent_ref()) and (index := qexcel.currentIndex()) >= 0:
            return drag_command(
                source=qexcel,
                type=qexcel._model_type_component,
                command_id="builtins:QDictOfWidgetEdit:select-tab",
                with_params={
                    "index": qexcel.currentIndex(),
                    "model_type": qexcel._model_type_component,
                },
                exec=False,
                desc=qexcel.tabText(index),
            )
        return None


class QDictOfWidgetEdit(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabBar(QRightClickableTabBar(self))
        self._is_editable = True
        self._model_type_component = StandardType.ANY
        self._model_type = StandardType.DICT
        self._extension_default: str | None = None
        self.currentChanged.connect(self._on_tab_changed)
        self._line_edit = QTabRenameLineEdit(self, allow_duplicate=False)

        # corner widget for adding new tab
        tb = QtW.QToolButton()
        tb.setText("+")
        tb.setFont(QtGui.QFont("Arial", 12, weight=15))
        tb.setToolTip("New Tab")
        tb.clicked.connect(self.add_new_tab)
        self.setCornerWidget(tb, QtCore.Qt.Corner.TopRightCorner)
        self.tabBar().right_clicked.connect(self._tabbar_right_clicked)

    def _default_widget(self) -> QtW.QWidget:
        raise NotImplementedError

    def _on_tab_changed(self, index: int):
        self.control_widget().update_for_component(self.widget(index))
        return None

    def _tabbar_right_clicked(self, index: int):
        if index < 0:  # Clicked on the empty space
            return
        else:  # Clicked on an existing tab
            menu = QtW.QMenu(self)
            rename_action = menu.addAction("Rename Tab")
            delete_action = menu.addAction("Delete Tab")
            action = menu.exec(QtGui.QCursor.pos())
            if action == rename_action:
                self._line_edit.start_edit(index)
            elif action == delete_action:
                self.removeTab(index)

    def add_new_tab(self):
        table = self._default_widget()
        self.addTab(table, f"Sheet-{self.count() + 1}")
        self.setCurrentIndex(self.count() - 1)
        self.control_widget().update_for_component(table)
        return None

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if not isinstance(value := model.value, Mapping):
            raise ValueError(f"Expected a dict, got {type(value)}")
        self.clear()
        for tab_name, each in value.items():
            table = self._default_widget()
            table.update_model(
                WidgetDataModel(value=each, type=self._model_type_component)
            )
            self.addTab(table, str(tab_name))
        if self.count() > 0:
            self.setCurrentIndex(0)
            self.control_widget().update_for_component(self.widget(0))
        self._model_type = model.type
        self._extension_default = model.extension_default
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        index = self.currentIndex()
        models: dict[str, WidgetDataModel] = {
            self.tabText(i): self.widget(i).to_model() for i in range(self.count())
        }
        return WidgetDataModel(
            value={tab_name: model.value for tab_name, model in models.items()},
            type=self.model_type(),
            extension_default=self._extension_default,
            metadata=DictMeta(
                current_tab=self.tabText(index),
                child_meta={
                    tab_name: model.metadata for tab_name, model in models.items()
                },
            ),
        )

    @validate_protocol
    def control_widget(self) -> "QTabControl":
        raise NotImplementedError

    @validate_protocol
    def model_type(self):
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return any(self.widget(i).is_modified() for i in range(self.count()))

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        for i in range(self.count()):
            self.widget(i).set_modified(value)

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @validate_protocol
    def is_editable(self) -> bool:
        return self._is_editable

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        self._is_editable = value
        for i in range(self.count()):
            self.widget(i).set_editable(value)

    @validate_protocol
    def allowed_drop_types(self) -> list[str]:
        return [self._model_type, self._model_type_component]

    @validate_protocol
    def dropped_callback(self, model: WidgetDataModel) -> DropResult:
        return DropResult(
            delete_input=True,
            command_id="builtins:QDictOfWidgetEdit:merge-tab",
            with_params={"incoming": model},
        )

    if TYPE_CHECKING:

        def tabBar(self) -> QRightClickableTabBar: ...


class QTabControl(QtW.QWidget):
    def update_for_component(self, widget: QtW.QWidget | None):
        raise NotImplementedError


@register_hidden_function(command_id="builtins:QDictOfWidgetEdit:select-tab")
def select_tab(model: WidgetDataModel) -> Parametric:
    def run(index: int, model_type: str) -> WidgetDataModel:
        d = dict(model.value)
        key = list(d.keys())[index]
        value = d[key]
        return WidgetDataModel(
            value=value,
            type=model_type,
            title=key,
        )

    return run


@register_hidden_function(command_id="builtins:QDictOfWidgetEdit:merge-tab")
def merge_tab(model: WidgetDataModel) -> Parametric:
    def run(incoming: WidgetDataModel) -> WidgetDataModel:
        out = dict(model.value)
        if incoming.is_subtype_of(StandardType.DICT):
            for key, value in dict(incoming.value).items():
                _update_dict_no_duplicate(out, key, value)
        else:
            _update_dict_no_duplicate(out, incoming.title, incoming.value)
        return model.with_value(out)

    return run


def _update_dict_no_duplicate(dict_: dict, key: str, value):
    if key not in dict_:
        dict_[key] = value
        return dict_

    if "-" in key and key.rsplit("-")[-1].isdigit():
        prefix, num_str = key.rsplit("-", 1)
        num = int(num_str) + 1
    else:
        prefix = key
        num = 0
    while f"{prefix}-{num}" in dict_:
        num += 1
    dict_[f"{prefix}-{num}"] = value
    return dict_
