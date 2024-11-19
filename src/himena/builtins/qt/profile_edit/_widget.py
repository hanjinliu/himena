from __future__ import annotations

from typing import Iterator, NamedTuple

from app_model import Application
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from himena.consts import MonospaceFontFamily
from himena.profile import define_app_profile
from himena.plugins import AppActionRegistry


class QProfileEditor(QtW.QDialog):
    """Widget to edit application profiles."""

    def __init__(self, app: Application):
        super().__init__()
        self._app = app
        layout = QtW.QVBoxLayout(self)
        self._name_label = QtW.QLineEdit(self)
        self._name_label.setText(app.name)
        self._name_label.setReadOnly(True)
        self._plugins_editor = QProfileTree(self)
        self._ok_button = QtW.QPushButton("OK", self)
        self._apply_button = QtW.QPushButton("Apply", self)
        self._cancel_button = QtW.QPushButton("Cancel", self)
        self._button_group = QtW.QWidget(self)
        button_layout = QtW.QHBoxLayout(self._button_group)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        button_layout.addWidget(self._ok_button)
        button_layout.addWidget(self._apply_button)
        button_layout.addWidget(self._cancel_button)

        layout.addWidget(self._name_label)
        layout.addWidget(self._plugins_editor)
        layout.addWidget(self._button_group)

        self._ok_button.clicked.connect(self._finish_edit)
        self._apply_button.clicked.connect(self._apply_changes)
        self._cancel_button.clicked.connect(self.reject)

    def _finish_edit(self):
        self._apply_changes()
        self.accept()

    def _apply_changes(self):
        plugins = self._plugins_editor.get_plugin_list()
        define_app_profile(self._name_label.text(), plugins)
        AppActionRegistry.instance().install_to(self._app)


class QProfileTree(QtW.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        font = QtGui.QFont(MonospaceFontFamily)
        self.setFont(font)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setIndentation(10)
        last_distribution: str | None = None
        current_toplevel_item: QtW.QTreeWidgetItem | None = None

        reg = AppActionRegistry.instance()
        installed_plugins = reg.installed_plugins

        for info in iter_plugin_info():
            if info.distribution != last_distribution:
                last_distribution = info.distribution
                if current_toplevel_item is not None:
                    current_toplevel_item.setExpanded(True)
                current_toplevel_item = QtW.QTreeWidgetItem([info.distribution])
                current_toplevel_item.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                current_toplevel_item.setCheckState(0, Qt.CheckState.Checked)
                self.addTopLevelItem(current_toplevel_item)
            item = QtW.QTreeWidgetItem([f"{info.name} ({info.place})", info.place])
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            if info.place in installed_plugins:
                item.setCheckState(0, Qt.CheckState.Checked)
            else:
                item.setCheckState(0, Qt.CheckState.Unchecked)
                current_toplevel_item.setCheckState(0, Qt.CheckState.Unchecked)
            current_toplevel_item.addChild(item)
        if current_toplevel_item is not None:
            current_toplevel_item.setExpanded(True)
        self.itemChanged.connect(self._on_item_changed)

    def get_plugin_list(self) -> list[str]:
        plugins = []
        for i in range(self.topLevelItemCount()):
            dist_item = self.topLevelItem(i)
            for j in range(dist_item.childCount()):
                plugin_item = dist_item.child(j)
                if plugin_item.checkState(0) == Qt.CheckState.Checked:
                    plugins.append(plugin_item.text(1))
        return plugins

    def _on_item_changed(self, item: QtW.QTreeWidgetItem, column: int):
        if item.parent() is None:
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, item.checkState(0))


def _not(x: Qt.CheckState) -> Qt.CheckState:
    if x == Qt.CheckState.Checked:
        state = Qt.CheckState.Unchecked
    else:
        state = Qt.CheckState.Checked
    return state


class HimenaPluginInfo(NamedTuple):
    name: str
    place: str
    version: str
    distribution: str

    def load(self):
        from importlib import import_module

        return import_module(self.place)


ENTRY_POINT_GROUP_NAME = "himena.plugin"


def iter_plugin_info() -> Iterator[HimenaPluginInfo]:
    from importlib.metadata import distributions

    for dist in distributions():
        for ep in dist.entry_points:
            if ep.group == ENTRY_POINT_GROUP_NAME:
                yield HimenaPluginInfo(ep.name, ep.value, dist.version, dist.name)
