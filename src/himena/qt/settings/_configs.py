from __future__ import annotations

from typing import TYPE_CHECKING
import warnings
from qtpy import QtWidgets as QtW, QtCore

from magicgui import widgets as mgw
from psygnal import throttled
from himena.profile import AppProfile
from himena.plugins import AppActionRegistry
from himena.qt.magicgui import get_type_map


if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QPluginConfigs(QtW.QScrollArea):
    """Widget for editing plugin configs.

    All the built-in and user-defined plugins are listed here. Any dict-like objects,
    including dataclass and pydantic.BaseModel, can be used as the config and will be
    converted into a widget by magicgui.
    """

    def __init__(self, ui: MainWindow):
        super().__init__()
        self.setWidgetResizable(True)
        self._ui = ui
        _central_widget = QtW.QWidget()
        self.setWidget(_central_widget)
        layout = QtW.QVBoxLayout(_central_widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        self._plugin_id_to_containers: dict[str, mgw.Container] = {}
        self._layout = layout
        self.add_config_forms()

    def add_config_forms(self):
        type_map = get_type_map()
        reg = AppActionRegistry.instance()
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


@throttled(timeout=100)
def _update_configs_throttled(prof: AppProfile, container: mgw.Container):
    prof.update_plugin_config(container.name, **container.asdict())


def _make_label_text(plugin_title: str, param: str, opt: dict) -> str:
    param_text = opt.pop("label", param.replace("_", " ").capitalize())
    return f'<font color="#808080">{plugin_title}:</font> {param_text}'
