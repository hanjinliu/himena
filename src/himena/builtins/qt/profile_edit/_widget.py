from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from himena.consts import MonospaceFontFamily
from himena.profile import define_app_profile, iter_app_profiles, AppProfile
from himena.plugins import dry_install_plugins


class QProfileEditor(QtW.QWidget):
    """Widget to edit application profiles."""

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout()
        self._combo_box = QtW.QComboBox(self)
        self._name_label = QtW.QLineEdit(self)
        self._name_label.setPlaceholderText("Profile name")
        self._plugins_editor = QPluginsEditor(self)
        self._edit_buttons = QPluginsEditButtons(self)
        layout.addWidget(self._combo_box)
        layout.addWidget(self._name_label)
        layout.addWidget(self._plugins_editor)
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
            self._plugins_editor.set_profile(prof)

    def _set_edit_mode(self, editable: bool):
        self._plugins_editor.set_item_editable(editable)
        self._name_label.setReadOnly(not editable)
        self._name_label.setVisible(not editable)
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
        plugins = self._plugins_editor.get_plugin_list()
        try:
            dry_install_plugins(plugins)
        except Exception:
            self._profile_changed(self._combo_box.currentIndex())  # reset inputs
            raise
        else:
            idx = self._combo_box.currentIndex()
            define_app_profile(self._name_label.text(), plugins)
            self._reload_profiles()
            self._combo_box.setCurrentIndex(idx)

    def _reload_profiles(self):
        self._combo_box.clear()
        prof_default = AppProfile.default()
        self._combo_box.addItem(prof_default.name, prof_default)
        for prof in iter_app_profiles():
            self._combo_box.addItem(prof.name, prof)
        self._profile_changed(0)


_KEYS_ACCEPT = frozenset(
    {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Delete, Qt.Key.Key_Home,
     Qt.Key.Key_End, Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
     Qt.Key.Key_Backspace, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown, Qt.Key.Key_Period,
     Qt.Key.Key_Underscore},
)  # fmt: skip


def _is_allowed_key(key: int) -> bool:
    return (
        key in _KEYS_ACCEPT
        or Qt.Key.Key_0 <= key <= Qt.Key.Key_9
        or Qt.Key.Key_A <= key <= Qt.Key.Key_Z
    )


class QPluginsEditor(QtW.QPlainTextEdit):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self.setReadOnly(True)

    def set_profile(self, profile: AppProfile):
        self.setPlainText("\n".join(profile.plugins))

    def set_item_editable(self, editable: bool):
        self.setReadOnly(not editable)

    def get_plugin_list(self) -> list[str]:
        text = self.toPlainText()
        return [_l.strip() for _l in text.splitlines() if _l.strip() != ""]

    def event(self, ev: QtCore.QEvent) -> bool:
        if ev.type() == QtCore.QEvent.Type.KeyPress:
            assert isinstance(ev, QtGui.QKeyEvent)
            _key = ev.key()
            if _is_allowed_key(_key):
                return super().event(ev)
            else:
                return True

        return super().event(ev)


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
