from __future__ import annotations

from typing import TYPE_CHECKING
import warnings
from qtpy import QtWidgets as QtW, QtCore

from magicgui import widgets as mgw
from magicgui.widgets.bases import ValuedContainerWidget
from psygnal import throttled
from himena.profile import AppProfile
from himena.plugins import AppActionRegistry
from himena.qt.magicgui import get_type_map, ToggleSwitch


if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QPluginConfigs(QtW.QWidget):
    """Widget for editing plugin configs.

    All the built-in and user-defined plugins are listed here. Any dict-like objects,
    including dataclass and pydantic.BaseModel, can be used as the config and will be
    converted into a widget by magicgui.
    """

    def __init__(self, ui: MainWindow):
        super().__init__()
        outer_layout = QtW.QVBoxLayout(self)
        self._filter_edit = QPluginConfigFilter(self)
        self._filter_edit.setToolTip("Filter plugin config parameters by label text.")
        outer_layout.addWidget(self._filter_edit)
        self._scroll_area = QtW.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        outer_layout.addWidget(self._scroll_area)
        self._ui = ui
        _central_widget = QtW.QWidget()
        self._scroll_area.setWidget(_central_widget)
        layout = QtW.QVBoxLayout(_central_widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        self._plugin_id_to_containers: dict[str, mgw.Container[mgw.Widget]] = {}
        self._layout = layout
        self.add_config_forms()

    def add_config_forms(self):
        type_map = get_type_map()
        reg = AppActionRegistry.instance()
        with type_map.type_registered(bool, widget_type=LabeledToggleSwitch):
            for plugin_id, plugin_config in self._ui.app_profile.plugin_configs.items():
                try:
                    widgets: list[mgw.Widget] = []
                    plugin_title = reg._plugin_default_configs[plugin_id].title
                    plugin_config = plugin_config.copy()
                    for param, opt in plugin_config.items():
                        if not isinstance(opt, dict):
                            raise TypeError(f"Invalid config for {plugin_id}: {param}")
                        _opt = opt.copy()
                        value = _opt.pop("value")
                        annotation = _opt.pop("annotation", None)
                        widget_type = None
                        if "choices" in _opt:
                            annotation = None
                            widget_type = "ComboBox"
                        widget = type_map.create_widget(
                            value=value,
                            annotation=annotation,
                            widget_type=widget_type,
                            label=_make_label_text(plugin_title, param, _opt),
                            options=_opt,
                            name=param,
                        )
                        if isinstance(widget, mgw.EmptyWidget):
                            warnings.warn(
                                f"Plugin config of {plugin_id!r} returned an empty widget.",
                                UserWarning,
                                stacklevel=2,
                            )
                        widgets.append(widget)
                    container = mgw.Container(widgets=widgets, name=plugin_id)
                    self._plugin_id_to_containers[plugin_id] = container
                    container.changed.connect(self._update_configs)
                    self._layout.addWidget(container.native)
                except Exception as e:
                    warnings.warn(f"Failed to create config for {plugin_id}: {e}")
        self._layout.addWidget(QtW.QWidget(), 1)  # spacer

    def _update_configs(self, container: mgw.Container):
        return _update_configs_throttled(self._ui.app_profile, container)


class QPluginConfigFilter(QtW.QLineEdit):
    def __init__(self, parent: QPluginConfigs):
        super().__init__(parent)
        self.setPlaceholderText("Type to filter ...")
        self.textChanged.connect(self._filter_configs)

    def parent(self) -> QPluginConfigs:
        return super().parent()

    def _filter_configs(self, text: str):
        return _filter_configs(self.parent(), text)


@throttled(timeout=100)
def _update_configs_throttled(prof: AppProfile, container: mgw.Container):
    prof.update_plugin_config(container.name, **container.asdict())


@throttled(timeout=100)
def _filter_configs(self: QPluginConfigs, text: str):
    text = text.strip().lower()
    empty = text == ""
    for container in self._plugin_id_to_containers.values():
        at_least_one_visible = False
        for child in container:
            vis = empty or text in _remove_html_from_label_text(child.label).lower()
            child.visible = vis
            at_least_one_visible = at_least_one_visible or vis
        container.visible = at_least_one_visible


_LEFT = '<b><font color="#808080">'
_RIGHT = "</font></b>"


def _make_label_text(plugin_title: str, param: str, opt: dict) -> str:
    param_text = opt.pop("label", param.replace("_", " ").capitalize())
    return f"{_LEFT}{plugin_title}:{_RIGHT} {param_text}"


def _remove_html_from_label_text(text: str):
    nchars = len(_LEFT)
    return "".join(text[nchars:].split(_RIGHT, 1))


class LabeledToggleSwitch(ValuedContainerWidget):
    def __init__(self, value=True, **kwargs):
        self._inner = ToggleSwitch(value=value, label="")
        widgets = [self._inner]
        kwargs["widgets"] = widgets
        super().__init__(value, **kwargs)
        self.margins = (0, 0, 0, 0)
        self._inner.changed.connect(self.changed.emit)

    def get_value(self):
        return self._inner.get_value()

    def set_value(self, value):
        return self._inner.set_value(value)
