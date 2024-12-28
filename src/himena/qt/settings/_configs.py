from __future__ import annotations

from typing import TYPE_CHECKING
import warnings
from qtpy import QtWidgets as QtW, QtCore

from magicgui import widgets as mgw
from psygnal import throttled
from himena.profile import AppProfile
from himena.qt._magicgui import get_type_map


if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QPluginConfigs(QtW.QScrollArea):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self.setWidgetResizable(True)
        self._ui = ui
        _central_widget = QtW.QWidget()
        self.setWidget(_central_widget)
        layout = QtW.QVBoxLayout(_central_widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        type_map = get_type_map()
        self._plugin_id_to_containers: dict[str, mgw.Container] = {}
        for plugin_id, plugin_config in ui.app_profile.plugin_configs.items():
            try:
                widgets: list[mgw.Widget] = []
                plugin_config = plugin_config.copy()
                plugin_title = plugin_config.pop(".title")
                for param, opt in plugin_config.items():
                    if not isinstance(opt, dict):
                        raise TypeError(f"Invalid config for {plugin_id}: {param}")
                    _opt = opt.copy()
                    value = _opt.pop("value")
                    annotation = _opt.pop("annotation", None)
                    label = f'<font color="#808080">{plugin_title}:</font> {_opt.pop("label", param)}'
                    widget = type_map.create_widget(
                        value=value,
                        annotation=annotation,
                        label=label,
                        options=_opt,
                        name=param,
                    )
                    widgets.append(widget)
                container = mgw.Container(widgets=widgets, name=plugin_id)
                self._plugin_id_to_containers[plugin_id] = container
                container.changed.connect(self._update_config)
                layout.addWidget(container.native)
            except Exception as e:
                warnings.warn(f"Failed to create config for {plugin_id}: {e}")
        layout.addWidget(QtW.QWidget(), 1)  # spacer

    def _update_config(self, container: mgw.Container):
        return _update_config_throttled(self._ui.app_profile, container)


@throttled(timeout=100)
def _update_config_throttled(prof: AppProfile, container: mgw.Container):
    prof.update_plugin_config(container.name, **container.asdict())
