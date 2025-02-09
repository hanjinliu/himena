from __future__ import annotations

from functools import wraps
import uuid
from typing import (
    Callable,
    Generic,
    Sequence,
    TypeVar,
    overload,
    TYPE_CHECKING,
)
import weakref

from app_model.types import Action, ToggleRule

from himena.types import DockArea, DockAreaString
from himena.consts import NO_RECORDING_FIELD
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
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings: KeyBindingsType | None = None,
    singleton: bool = False,
    plugin_configs: PluginConfigType | None = None,
    command_id: str | None = None,
) -> _F: ...


@overload
def register_dock_widget_action(
    widget_factory: None = None,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings: KeyBindingsType | None = None,
    singleton: bool = False,
    plugin_configs: PluginConfigType | None = None,
    command_id: str | None = None,
) -> Callable[[_F], _F]: ...


def register_dock_widget_action(
    widget_factory=None,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings=None,
    singleton: bool = False,
    plugin_configs: PluginConfigType | None = None,
    command_id: str | None = None,
):
    """
    Register a widget factory as a dock widget function.

    Parameters
    ----------
    widget_factory : callable, optional
        Class of dock widget, or a factory function for the dock widget.
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
    """
    kbs = normalize_keybindings(keybindings)

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


# TODO: Implement the following function
# @overload
# def register_widget_action(
#     widget_factory: _F,
#     *,
#     menus: str | Sequence[str] = "plugins",
#     title: str | None = None,
#     area: DockArea | DockAreaString = DockArea.RIGHT,
#     allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
#     keybindings: KeyBindingsType | None = None,
#     singleton: bool = False,
#     plugin_configs: PluginConfigType | None = None,
#     command_id: str | None = None,
# ) -> _F: ...

# @overload
# def register_widget_action(
#     widget_factory: None = None,
#     *,
#     menus: str | Sequence[str] = "plugins",
#     title: str | None = None,
#     area: DockArea | DockAreaString = DockArea.RIGHT,
#     allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
#     keybindings: KeyBindingsType | None = None,
#     singleton: bool = False,
#     plugin_configs: PluginConfigType | None = None,
#     command_id: str | None = None,
# ) -> Callable[[_F], _F]: ...

# def register_widget_action(
#     widget_factory=None,
#     *,
#     menus: str | Sequence[str] = "plugins",
#     title: str | None = None,
#     keybindings: KeyBindingsType | None = None,
#     plugin_configs: PluginConfigType | None = None,
#     command_id: str | None = None,
# ):
#     """
#     Register a widget factory as a widget action.

#     Parameters
#     ----------
#     widget_factory : callable, optional
#         Class of widget, or a factory function for the widget.
#     title : str, optional
#         Title of the widget.
#     keybindings : sequence of keybinding rule, optional
#         Keybindings to trigger the widget.
#     plugin_configs : dict, dataclass or pydantic.BaseModel, optional
#         Default configuration for the plugin. This config will be saved in the
#         application profile and will be used to update the widget via the method
#         `update_configs(self, cfg) -> None`. This argument must be a dict, dataclass
#         or pydantic.BaseModel. If a dict, the format must be like:
#         >>> plugin_configs = {
#         ...    "config_0": {"value": 0, "tooltip": ...},
#         ...    "config_1": {"value": "xyz", "tooltip": ...},
#         ... }
#         where only "value" is required. If a dataclass or pydantic.BaseModel, field
#         objects will be used instead of the dict.
#         >>> @dataclass
#         ... class MyPluginConfig:
#         ...     config_0: int = Field(default=0, metadata={"tooltip": ...})
#         ...     config_1: str = Field(default="xyz", metadata={"tooltip": ...})
#         ... plugin_configs = MyPluginConfig()
#     command_id : str, optional
#         Command ID. If not given, the function name will be used.
#     """
#     kbs = normalize_keybindings(keybindings)

#     def _inner(wf: Callable):
#         _command_id = command_id_from_func(wf, command_id)
#         _callback = WidgetCallback(
#             wf,
#             title=title,
#             uuid=uuid.uuid4(),
#             command_id=_command_id,
#         )
#         action = Action(
#             id=_command_id,
#             title=_callback._title,
#             tooltip=tooltip_from_func(wf),
#             callback=_callback,
#             menus=norm_menus(menus),
#             keybindings=kbs,
#         )
#         reg = AppActionRegistry.instance()
#         reg.add_action(action)
#         if plugin_configs:
#             cfg_type = type(plugin_configs)
#             reg._plugin_default_configs[_command_id] = PluginConfigTuple(
#                 _callback._title, plugin_configs, cfg_type,
#             )
#         return wf

#     return _inner if widget_factory is None else _inner(widget_factory)


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
        if widget := self._widget_ref():
            return widget.visible
        return False


# class WidgetCallback(WidgetCallbackBase["SubWindow"]):
#     """Callback for registering widgets."""

#     def __init__(
#         self,
#         func: Callable,
#         title: str | None,
#         uuid: uuid.UUID | None,
#         command_id: str,
#     ):
#         super().__init__(func, title=title, uuid=uuid, command_id=command_id)

#     def __call__(self, ui: MainWindow) -> SubWindow:
#         try:
#             widget = self._func(ui)
#         except TypeError:
#             widget = self._func()
#         win = ui.add_widget(
#             widget,
#             title=self._title,
#             _identifier=self._uuid,
#         )
#         self._all_widgets.add(widget)
#         self._widget_ref = weakref.ref(widget)
#         plugin_configs = ui.app_profile.plugin_configs.get(self._command_id)
#         if plugin_configs:
#             if not hasattr(widget, 'update_configs'):
#                 raise ValueError(
#                     "The widget must have 'update_configs' method if plugin config "
#                     "fields are given.",
#                 )
#             params = {}
#             for k, v in plugin_configs.items():
#                 params[k] = v["value"]
#             widget.update_configs(params)
#         return win


def _normalize_title(title: str | None, func: Callable) -> str:
    if title is None:
        return func.__name__.replace("_", " ").title()
    return title
