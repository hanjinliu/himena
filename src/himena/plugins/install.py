from __future__ import annotations

import logging
import traceback
from importlib import import_module
from typing import TYPE_CHECKING
from pathlib import Path
from timeit import default_timer as timer
from app_model.types import KeyBindingRule
from dataclasses import dataclass, field
from himena.plugins.config import config_field

if TYPE_CHECKING:
    from himena.profile import AppProfile
    from himena._app_model import HimenaApplication
    from himena.plugins.widget_class import PluginConfigType

_LOGGER = logging.getLogger(__name__)


def install_plugins(
    app: HimenaApplication, plugins: list[str]
) -> list[PluginInstallResult]:
    """Install plugins to the application."""
    from himena.plugins import AppActionRegistry
    from himena.profile import load_app_profile

    reg = AppActionRegistry.instance()
    results = []
    show_import_time = app.attributes.get("print_import_time", False)
    if show_import_time:
        print("==================")
        print("Plugin import time")
        print("==================")
    for name in plugins:
        if name in reg._installed_plugins:
            continue
        _time_0 = timer()
        _exc = None
        if isinstance(name, str):
            if name.endswith(".py"):
                if not Path(name).exists():
                    _LOGGER.error(
                        f"Plugin file {name} does not exists but is listed in the "
                        "application profile."
                    )
                    continue
                import runpy

                runpy.run_path(name)
            else:
                try:
                    import_module(name)
                except ModuleNotFoundError:
                    _LOGGER.error(
                        f"Plugin module {name} is not installed but is listed in the "
                        "application profile."
                    )
                    continue
                except Exception as e:
                    msg = "".join(
                        traceback.format_exception(type(e), e, e.__traceback__)
                    )
                    _LOGGER.error(
                        f"Error installing plugin {name}, traceback follows:\n{msg}"
                    )
                    _exc = e
        else:
            raise TypeError(f"Invalid plugin type: {type(name)}")
        _msec = (timer() - _time_0) * 1000
        if show_import_time and _exc is None:
            color = _color_for_time(_msec)
            print(f"{color}{name}\t{_msec:.3f} msec\033[0m")
        results.append(PluginInstallResult(name, _msec, _exc))
    reg.install_to(app)
    reg._installed_plugins.extend(plugins)
    prof = load_app_profile(app.name)

    for cfg_key, cfg in reg._plugin_default_configs.items():
        cfg_dict = cfg.as_dict()
        cfg_dict_old = prof.plugin_configs.get(cfg_key, {})
        # NOTE: if same config was updated during development, it may not have some keys
        for k, v in cfg_dict.items():
            if k not in cfg_dict_old:
                cfg_dict_old[k] = v
        prof.plugin_configs[cfg_key] = cfg_dict_old

    prof.save()
    return results


def override_keybindings(app: HimenaApplication, prof: AppProfile) -> None:
    """Override keybindings in the application."""
    for ko in prof.keybinding_overrides:
        if kb := app.keybindings.get_keybinding(ko.command_id):
            app.keybindings._keybindings.remove(kb)
        app.keybindings.register_keybinding_rule(
            ko.command_id,
            KeyBindingRule(primary=ko.key),
        )


@dataclass
class GlobalConfig:
    num_recent_files_to_show: int = config_field(default=10)
    num_recent_sessions_to_show: int = config_field(default=3)
    subwindow_bar_height: int = config_field(default=18, min=10, max=45)


def install_default_configs() -> None:
    register_config("himena", "Global Settings", GlobalConfig)


def register_config(plugin_id: str, title: str, cfg: PluginConfigType) -> None:
    from himena.plugins.actions import AppActionRegistry, PluginConfigTuple

    reg = AppActionRegistry.instance()
    tup = PluginConfigTuple(title, cfg, type(cfg))
    cfg_dict = tup.as_dict()
    for key, value_dict in cfg_dict.items():
        assert isinstance(value_dict, dict)
        if value_dict.get("value") is None and "choices" not in value_dict:
            raise ValueError(
                f"Key {key!r} ofr config {cfg!r} must have a default value or choices. "
                f"Equivalent dict was:\n{cfg_dict!r}"
            )
    reg._plugin_default_configs[plugin_id] = PluginConfigTuple(title, cfg, type(cfg))


@dataclass
class PluginInstallResult:
    plugin: str
    time: float = field(default=0.0)
    error: Exception | None = None


def _color_for_time(msec: float) -> str:
    """Return a color code for the given time in milliseconds."""
    if msec < 80:
        return "\033[92m"  # green
    elif msec < 700:
        return "\033[93m"  # yellow
    else:
        return "\033[91m"  # red
