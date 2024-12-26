from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore

from magicgui import widgets as mgw
from himena.plugins.actions import AppActionRegistry, WidgetCallbackBase
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

    def _update_config(self, container: mgw.Container):
        reg = AppActionRegistry.instance()
        plugin_id = container.name
        configs = self._ui.app_profile.plugin_configs.copy()
        if plugin_id in configs:
            # Profile already has the plugin config
            config = configs[plugin_id].copy()
        else:
            # Profile does not have the plugin config. The config is only temporarily
            # registered in the registry.
            config = reg._plugin_default_configs[plugin_id].copy()
        for k, v in container.asdict().items():
            config[k]["value"] = v
        configs[plugin_id] = config
        self._ui.app_profile.with_plugin_configs(configs).save()

        # update existing dock widgets with the new config
        params = {}
        for key, opt in config.items():
            if key.startswith("."):
                continue
            params[key] = opt["value"]
        if cb := WidgetCallbackBase.instance_for_command_id(plugin_id):
            for dock in cb._all_widgets:
                dock.widget.update_config(**params)
