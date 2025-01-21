from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from himena.consts import MonospaceFontFamily
from himena.plugins import AppActionRegistry
from himena.utils.entries import iter_plugin_info
from himena.qt.settings._shared import QInstruction

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QPluginListEditor(QtW.QWidget):
    """Widget to edit plugin list."""

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._app = ui.model_app
        layout = QtW.QVBoxLayout(self)
        _instruction1 = QInstruction(
            f"Select plugins to be included in <b><code>himena {self._app.name}</code>"
            "</b>.<br>Click <b>Apply</b> to save changes.",
        )
        self._plugins_editor = QAvaliablePluginsTree(self)
        self._plugins_editor.stateChanged.connect(self._enabled_apply_button)

        _instruction2 = QInstruction("List of '.py' files as unpackaged plugins.")
        self._additional_plugin_list = QtW.QPlainTextEdit()
        self._additional_plugin_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._additional_plugin_list.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self._additional_plugin_list.setFont(QtGui.QFont(MonospaceFontFamily))
        self._additional_plugin_list.setFixedHeight(120)
        self._additional_plugin_list.setPlaceholderText("e.g. path/to/file.py")
        for plugin_name in ui.app_profile.plugins:
            if plugin_name.endswith(".py") and Path(plugin_name).exists():
                self._additional_plugin_list.appendPlainText(plugin_name + "\n")

        self._apply_button = QtW.QPushButton("Apply", self)
        self._button_group = QtW.QWidget(self)
        button_layout = QtW.QHBoxLayout(self._button_group)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        button_layout.addWidget(self._apply_button)

        layout.addWidget(_instruction1)
        layout.addWidget(self._plugins_editor)
        layout.addWidget(_instruction2)
        layout.addWidget(self._additional_plugin_list)
        layout.addWidget(self._button_group)

        self._apply_button.clicked.connect(self._apply_changes)
        self._apply_button.setEnabled(False)
        self._additional_plugin_list.textChanged.connect(self._enabled_apply_button)

    def _apply_changes(self):
        plugins = self._plugins_editor.get_plugin_list()
        for line in self._additional_plugin_list.toPlainText().splitlines():
            line = line.strip()
            if line:
                plugins.append(line)
        new_prof = self._ui.app_profile.with_plugins(plugins)
        AppActionRegistry.instance().install_to(self._app)
        new_prof.save()
        self._apply_button.setEnabled(False)

    def _enabled_apply_button(self):
        self._apply_button.setEnabled(True)


class QAvaliablePluginsTree(QtW.QTreeWidget):
    stateChanged = QtCore.Signal()

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
        self.stateChanged.emit()
