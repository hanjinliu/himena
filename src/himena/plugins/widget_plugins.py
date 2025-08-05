from __future__ import annotations

from contextlib import contextmanager, suppress
from functools import wraps
import uuid
from typing import (
    Callable,
    Generic,
    Iterator,
    Sequence,
    TypeVar,
    overload,
    TYPE_CHECKING,
)
import weakref

from app_model.types import Action, ToggleRule

from himena.types import DockArea, DockAreaString
from himena.consts import NO_RECORDING_FIELD, MenuId
from himena.plugins.actions import (
    normalize_keybindings,
    AppActionRegistry,
    command_id_from_func,
    tooltip_from_func,
    norm_menus,
    PluginConfigTuple,
)

if TYPE_CHECKING:
    from typing import Self
    from himena.widgets import MainWindow, DockWidget
    from himena.widgets._wrapper import WidgetWrapper
    from himena.plugins.actions import KeyBindingsType, PluginConfigType

_F = TypeVar("_F", bound=Callable)
_W = TypeVar("_W", bound="WidgetWrapper")


@overload
def register_dock_widget_action(
    widget_factory: _F,
    *,
    menus: str | Sequence[str] | None = None,
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings: KeyBindingsType | None = None,
    singleton: bool = False,
    plugin_configs: PluginConfigType | None = None,
    command_id: str | None = None,
    icon: str | None = None,
) -> _F: ...


@overload
def register_dock_widget_action(
    widget_factory: None = None,
    *,
    menus: str | Sequence[str] | None = None,
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings: KeyBindingsType | None = None,
    singleton: bool = False,
    plugin_configs: PluginConfigType | None = None,
    command_id: str | None = None,
    icon: str | None = None,
) -> Callable[[_F], _F]: ...


def register_dock_widget_action(
    widget_factory=None,
    *,
    menus: str | Sequence[str] | None = None,
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings=None,
    singleton: bool = False,
    plugin_configs: PluginConfigType | None = None,
    command_id: str | None = None,
    icon: str | None = None,
):
    """Register a widget factory as a dock widget function.

    Parameters
    ----------
    widget_factory : callable, optional
        Class of dock widget, or a factory function for the dock widget.
    menus : str or sequence of str, optional
        Menu ID or list of menu IDs where the action will be added.
    title : str, optional
        Title of the dock widget.
    area : DockArea or DockAreaString, optional
        Initial area of the dock widget.
    allowed_areas : sequence of DockArea or DockAreaString, optional
        List of areas that is allowed for the dock widget.
    keybindings : sequence of keybinding rule, optional
        Keybindings to trigger the dock widget.
    singleton : bool, default False
        If true, the registered dock widget will constructed only once.
    plugin_configs : dict, dataclass or pydantic.BaseModel, optional
        Default configuration for the plugin. This config will be saved in the
        application profile and will be used to update the dock widget via the method
        `update_configs(self, cfg) -> None`. This argument must be a dict, dataclass
        or pydantic.BaseModel. If a dict, the format must be like:

        ``` python
        plugin_configs = {
           "config_0": {"value": 0, "tooltip": ...},
           "config_1": {"value": "xyz", "tooltip": ...},
        }
        ```

        where only "value" is required. If a dataclass or pydantic.BaseModel, field
        objects will be used instead of the dict.

        ``` python
        @dataclass
        class MyPluginConfig:
            config_0: int = Field(default=0, metadata={"tooltip": ...})
            config_1: str = Field(default="xyz", metadata={"tooltip": ...})
        plugin_configs = MyPluginConfig()
        ```
    command_id : str, optional
        Command ID. If not given, the function name will be used.
    icon : str, optional
        Iconify icon key.
    """
    kbs = normalize_keybindings(keybindings)
    if menus is None:
        menus = [MenuId.TOOLS_DOCK]

    def _inner(wf: Callable):
        _command_id = command_id_from_func(wf, command_id)
        _callback = DockWidgetCallback(
            wf,
            title=title,
            area=area,
            allowed_areas=allowed_areas,
            singleton=singleton,
            uuid=uuid.uuid4(),
            command_id=_command_id,
        )
        if singleton:
            toggle_rule = ToggleRule(get_current=_callback.widget_visible)
        else:
            toggle_rule = None
        action = Action(
            id=_command_id,
            title=_callback._title,
            tooltip=tooltip_from_func(wf),
            callback=_callback,
            menus=norm_menus(menus),
            keybindings=kbs,
            toggled=toggle_rule,
            icon=icon,
            icon_visible_in_menu=False,
        )
        reg = AppActionRegistry.instance()
        reg.add_action(action)
        if plugin_configs:
            cfg_type = type(plugin_configs)
            reg._plugin_default_configs[_command_id] = PluginConfigTuple(
                _callback._title,
                plugin_configs,
                cfg_type,
            )
        return wf

    return _inner if widget_factory is None else _inner(widget_factory)


class WidgetCallbackBase(Generic[_W]):
    _instance_map = weakref.WeakValueDictionary[str, "Self"]()

    def __init__(
        self,
        func: Callable,
        title: str | None,
        uuid: uuid.UUID | None,
        command_id: str,
    ):
        self._func = func
        self._title = _normalize_title(title, func)
        self._uuid = uuid
        self._command_id = command_id
        # if singleton, retain the weak reference to the dock widget
        self._widget_ref: Callable[[], _W | None] = lambda: None
        self._all_widgets: weakref.WeakSet[_W] = weakref.WeakSet()
        wraps(func)(self)
        self.__annotations__ = {"ui": "MainWindow"}
        setattr(self, NO_RECORDING_FIELD, True)
        self.__class__._instance_map[command_id] = self

    @classmethod
    def instance_for_command_id(cls, command_id: str) -> Self | None:
        """Get the callback instance for the given command ID."""
        return WidgetCallbackBase._instance_map.get(command_id)


class DockWidgetCallback(WidgetCallbackBase["DockWidget"]):
    """Callback for registering dock widgets."""

    def __init__(
        self,
        func: Callable,
        title: str | None,
        area: DockArea | DockAreaString,
        allowed_areas: Sequence[DockArea | DockAreaString] | None,
        singleton: bool,
        uuid: uuid.UUID | None,
        command_id: str,
    ):
        super().__init__(func, title=title, uuid=uuid, command_id=command_id)
        self._singleton = singleton
        self._area = area
        self._allowed_areas = allowed_areas

    def __call__(self, ui: MainWindow) -> DockWidget:
        if self._singleton:
            if _dock := ui.dock_widgets.widget_for_id(self._uuid):
                _dock.visible = not _dock.visible
                return _dock
        try:
            widget = self._func(ui)
        except TypeError:
            widget = self._func()
        dock = ui.add_dock_widget(
            widget,
            title=self._title,
            area=self._area,
            allowed_areas=self._allowed_areas,
            _identifier=self._uuid,
        )
        dock._command_id = self._command_id
        self._all_widgets.add(dock)
        self._widget_ref = weakref.ref(dock)
        plugin_configs = ui.app_profile.plugin_configs.get(self._command_id)
        if plugin_configs:
            if not dock._has_update_configs:
                raise ValueError(
                    "The widget must have 'update_configs' method if plugin config "
                    "fields are given.",
                )
            params = {}
            for k, v in plugin_configs.items():
                params[k] = v["value"]
            dock.update_configs(params)
        return dock

    def widget_visible(self) -> bool:
        """Used for the toggle rule of the Action."""
        with suppress(RuntimeError):
            if widget := self._widget_ref():
                return widget.visible
        return False


def _normalize_title(title: str | None, func: Callable) -> str:
    if title is None:
        return func.__name__.replace("_", " ").title()
    return title


_C = TypeVar("_C", bound="PluginConfigType")


def _get_plugin_config(
    ui: MainWindow,
    config_class: type[_C],
    plugin_id: str | None = None,
) -> tuple[str, PluginConfigTuple]:
    if isinstance(config_class, str):
        if plugin_id is not None:
            raise TypeError("No overload matches the input.")
        _config_class, _plugin_id = None, config_class
    else:
        _config_class = config_class
        _plugin_id = plugin_id

    reg = AppActionRegistry.instance()
    if _plugin_id is None:
        for _id, _config in reg._plugin_default_configs.items():
            if isinstance(_config.config, _config_class):
                _plugin_id = _id
                break
        else:
            raise ValueError(
                f"Cannot find plugin ID for the config class: {config_class}."
            )
    config_dict = {
        k: v["value"] for k, v in ui.app_profile.plugin_configs[_plugin_id].items()
    }
    plugin_config = reg._plugin_default_configs[_plugin_id].updated(config_dict)
    if not isinstance(plugin_config.config, _config_class):
        raise TypeError(
            f"Plugin ID {_plugin_id} does not match the config class {config_class}."
        )
    return _plugin_id, plugin_config


def get_config(
    config_class: type[_C],
    plugin_id: str | None = None,
) -> _C | None:
    from himena.widgets import current_instance

    ui = current_instance()
    try:
        return _get_plugin_config(ui, config_class, plugin_id)[1].config
    except ValueError:
        return None


@overload
@contextmanager
def update_config_context(
    plugin_id: str,
    *,
    update_widget: bool = False,
) -> Iterator[PluginConfigType]: ...


@overload
@contextmanager
def update_config_context(
    config_class: type[_C],
    plugin_id: str | None = None,
    *,
    update_widget: bool = False,
) -> Iterator[_C]: ...


@contextmanager
def update_config_context(
    config_class: type | str,
    plugin_id: str | None = None,
    *,
    update_widget: bool = False,
):
    """Context manager for updating plugin config.

    If a config object is updated within the context, it will be saved to the profile
    and optionally trigger the update of the widget if `update_widget` is True.

    Examples
    --------

    ``` python
    with update_config_context(config_class=MyConfig) as cfg:
        cfg.some_attr = ...
    ```

    """
    from himena.widgets import current_instance

    ui = current_instance()
    plugin_id, plugin_config = _get_plugin_config(ui, config_class, plugin_id)
    cur_config = plugin_config.config
    yield cur_config
    prof = ui.app_profile
    all_configs = prof.plugin_configs.copy()

    cfg_dict = all_configs[plugin_id] = plugin_config.as_dict()
    prof.with_plugin_configs(all_configs).save()

    # update existing dock widgets with the new config
    if update_widget and (cb := WidgetCallbackBase.instance_for_command_id(plugin_id)):
        params = {}
        for key, opt in cfg_dict.items():
            params[key] = opt["value"]
        for widget in cb._all_widgets:
            # the internal widget should always has the method "update_configs"
            widget.update_configs(params)
