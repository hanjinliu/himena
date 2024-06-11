from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui, QtCore
from royalapp.qt._qt_consts import MonospaceFontFamily
from royalapp.profile import define_app_profile, iter_app_profiles, AppProfile
from royalapp.plugins import dry_install_plugins


class QProfileEditor(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout()
        self._combo_box = QtW.QComboBox(self)
        self._name_label = QtW.QLineEdit(self)
        self._name_label.setPlaceholderText("Profile name")
        self._list_widget = QPluginsListWidget(self)
        self._edit_buttons = QPluginsEditButtons(self)
        layout.addWidget(self._combo_box)
        layout.addWidget(self._name_label)
        layout.addWidget(self._list_widget)
        layout.addWidget(self._edit_buttons)
        self.setLayout(layout)

        self._edit_buttons.set_edit_mode(False)
        self._name_label.setReadOnly(True)

        self._reload_profiles()
        self._combo_box.currentIndexChanged.connect(self._profile_changed)

        self._edit_buttons.cancel_requested.connect(self._cancel_edit)
        self._edit_buttons.edit_requested.connect(self._start_edit)
        self._edit_buttons.save_requested.connect(self._finish_edit)

    def _profile_changed(self, index: int):
        prof = self._combo_box.itemData(index)
        if isinstance(prof, AppProfile):
            self._name_label.setText(prof.name)
            self._list_widget.set_profile(prof)

    def _set_edit_mode(self, editable: bool):
        self._list_widget.set_item_editable(editable)
        self._name_label.setReadOnly(not editable)
        self._edit_buttons.set_edit_mode(editable)

    def _start_edit(self):
        self._set_edit_mode(True)

    def _cancel_edit(self):
        self._set_edit_mode(False)
        self._profile_changed(self._combo_box.currentIndex())  # reset inputs

    def _finish_edit(self):
        self._set_edit_mode(False)
        existing_texts = [
            self._combo_box.itemText(i) for i in range(self._combo_box.count())
        ]
        if (_name := self._name_label.text()) in existing_texts:
            answer = QtW.QMessageBox.warning(
                self,
                "Warning",
                f"Profile {_name!r} already exists. Overwrite?",
            )
            if answer == QtW.QMessageBox.StandardButton.No:
                return
        plugins = self._list_widget.get_plugin_list()
        try:
            dry_install_plugins(plugins)
        except Exception:
            self._profile_changed(self._combo_box.currentIndex())  # reset inputs
            raise
        else:
            define_app_profile(self._name_label.text(), plugins)
            self._reload_profiles()

    def _reload_profiles(self):
        self._combo_box.clear()
        prof_default = AppProfile.default()
        self._combo_box.addItem(prof_default.name, prof_default)
        for prof in iter_app_profiles():
            self._combo_box.addItem(prof.name, prof)
        self._profile_changed(0)


class QPluginsListWidget(QtW.QListWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self._item_editable = False

    def set_profile(self, profile: AppProfile):
        self.clear()
        for plugin in profile.plugins:
            item = QtW.QListWidgetItem(plugin, self)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            self.addItem(item)

    def enter_new_plugin(self):
        self.addItem("")
        new_item = self.item(self.count() - 1)
        assert new_item is not None
        self.editItem(new_item)

    def set_item_editable(self, editable: bool):
        if editable:
            _trig = (
                QtW.QAbstractItemView.EditTrigger.DoubleClicked
                | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
            )
        else:
            _trig = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
        self.setEditTriggers(_trig)
        self._item_editable = editable

    def get_plugin_list(self) -> list[str]:
        plugins: list[str] = []
        for i in range(self.count()):
            item = self.item(i)
            if item is None:
                continue
            text = item.text()
            if text == "":
                continue
            plugins.append(text)
        return plugins

    def keyPressEvent(self, e: QtGui.QKeyEvent | None) -> None:
        if (
            e.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier
            and e.key() == QtCore.Qt.Key.Key_Delete
        ):
            if self._item_editable:
                for item in self.selectedItems():
                    self.takeItem(self.row(item))
        elif (
            e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            and e.key() == QtCore.Qt.Key.Key_N
        ):
            if self._item_editable:
                self.enter_new_plugin()
        else:
            return super().keyPressEvent(e)


class QPluginsEditButtons(QtW.QWidget):
    edit_requested = QtCore.Signal()
    save_requested = QtCore.Signal()
    cancel_requested = QtCore.Signal()

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)
        self._save_btn = self.add_button("Save", self.save_requested.emit)
        self._enter_edit_btn = self.add_button("Edit", self._edit_clicked)

    def add_button(self, text: str, slot) -> QtW.QPushButton:
        btn = QtW.QPushButton(text, self)
        self.layout().addWidget(btn)
        btn.clicked.connect(slot)
        return btn

    def set_edit_mode(self, editable: bool):
        if editable:
            self._enter_edit_btn.setText("Cancel")
            self._save_btn.setVisible(True)
        else:
            self._enter_edit_btn.setText("Edit")
            self._save_btn.setVisible(False)

    def _edit_clicked(self):
        if self._enter_edit_btn.text() == "Edit":
            self.edit_requested.emit()
        else:
            self.cancel_requested.emit()
