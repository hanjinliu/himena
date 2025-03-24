from __future__ import annotations

from dataclasses import is_dataclass, fields
from functools import reduce
import operator
import logging
from copy import deepcopy
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Sequence,
    TypeVar,
    overload,
    TYPE_CHECKING,
)

from pydantic_compat import BaseModel

from app_model import Action
from app_model.types import SubmenuItem, KeyBindingRule
from app_model.expressions import BoolOp

from himena._app_model import AppContext as ctx
from himena.consts import MenuId
from himena import _utils
from himena.types import WidgetDataModel
from himena.utils.collections import OrderedSet

if TYPE_CHECKING:
    from himena._app_model import HimenaApplication

    KeyBindingsType = str | KeyBindingRule | Sequence[str] | Sequence[KeyBindingRule]
    PluginConfigType = Any

_F = TypeVar("_F", bound=Callable)
_LOGGER = logging.getLogger(__name__)


class PluginConfigTuple(NamedTuple):
    title: str
    config: PluginConfigType
    config_class: type

    def as_dict(self) -> dict[str, Any]:
        """Convert the config into a normalized dictionary."""
        config = self.config
        if isinstance(config, Mapping):
            out = deepcopy(config)
        elif is_dataclass(config):
            out = {}
            for _f in fields(config):
                out[_f.name] = {"value": getattr(config, _f.name), **_f.metadata}
        elif isinstance(config, BaseModel):
            out = {}
            for _fname, _finfo in config.model_fields.items():
                options = {}
                if tooltip := _finfo.description:
                    options["tooltip"] = tooltip
                options.update(_finfo.metadata)
                out[_f] = {"value": getattr(config, _fname), **options}
        else:
            raise TypeError(
                "Plugin config type must be dict, dataclass or pydantic.BaseModel, but "
                f"got {config!r}"
            )
        return out


class AppActionRegistry:
    _global_instance: AppActionRegistry | None = None

    def __init__(self):
        self._actions: dict[str, Action] = {}
        self._actions_dynamic: set[str] = set()
        self._submenu_titles: dict[str, str] = {
            MenuId.FILE_NEW: "New ...",
            MenuId.TOOLS_DOCK: "Dock widgets",
        }
        self._submenu_groups: dict[str, str] = {
            MenuId.FILE_NEW: "00_new",
            MenuId.TOOLS_DOCK: "00_dock",
        }
        self._installed_plugins: list[str] = []
        self._plugin_default_configs: dict[str, PluginConfigTuple] = {}

    @classmethod
    def instance(cls) -> AppActionRegistry:
        """Get the global instance of the registry."""
        if cls._global_instance is None:
            cls._global_instance = cls()
        return cls._global_instance

    def add_action(self, action: Action, is_dynamic: bool = False) -> None:
        """Add an action to the registry."""
        id_ = action.id
        if id_ in self._actions:
            raise ValueError(f"Action ID {id_} already exists.")
        self._actions[id_] = action
        if is_dynamic:
            self._actions_dynamic.add(id_)

    @property
    def installed_plugins(self) -> list[str]:
        """List of modules or python paths that are installed as plugins."""
        return self._installed_plugins

    def iter_actions(self, app: HimenaApplication) -> Iterator[Action]:
        for id_, action in self._actions.items():
            if id_ not in app.commands:
                yield action

    def submenu_title(self, id: str) -> str:
        """Get the title of a submenu."""
        if title := self._submenu_titles.get(id):
            return title
        return id.split("/")[-1].title()

    def submenu_group(self, id: str) -> str | None:
        """Get the group of a submenu."""
        return self._submenu_groups.get(id, None)

    @property
    def submenu_titles(self) -> dict[str, str]:
        return self._submenu_titles

    def install_to(
        self,
        app: HimenaApplication,
        actions: list[Action] | None = None,
    ) -> list[str]:
        """Install actions to the application.

        This method automatically adds submenus if they are not already exists, and
        returns the list of added root menu IDs. Note that this does NOT updates the
        GUI menubar and toolbar.
        """
        # look for existing menu items
        if actions is None:
            actions = list(self.iter_actions(app))
        existing_menu_ids = {_id.value for _id in MenuId if "/" not in _id.value}
        for menu_id, menu in app.menus:
            existing_menu_ids.add(menu_id)
            for each in menu:
                if isinstance(each, SubmenuItem):
                    existing_menu_ids.add(each.submenu)

        added_menu_ids = OrderedSet[str]()
        for action in actions:
            if action.menus is not None:
                ids = [a.id for a in action.menus]
                added_menu_ids.update(ids)

        # add submenus if not exists
        to_add: list[tuple[str, SubmenuItem]] = []
        new_menu_ids: list[str] = []

        for place in added_menu_ids - existing_menu_ids:
            place_components = place.split("/")
            if len(place_components) == 1:
                new_menu_ids.append(place)
            for i in range(1, len(place_components)):
                menu_id = "/".join(place_components[:i])
                submenu = "/".join(place_components[: i + 1])
                if submenu in existing_menu_ids:
                    continue
                title = self.submenu_title(submenu)
                group = self.submenu_group(submenu)
                item = SubmenuItem(title=title, submenu=submenu, group=group)
                to_add.append((menu_id, item))

        app.register_actions(actions)
        app.menus.append_menu_items(to_add)
        app._dynamic_command_ids.update(self._actions_dynamic)
        return new_menu_ids


def norm_menus(menus: str | Sequence[str]) -> list[str]:
    if isinstance(menus, str):
        return [menus]
    return list(menus)


def _norm_menus_with_group(menus: str | Sequence[str], group: str) -> list[dict]:
    return [{"id": menu, "group": group} for menu in norm_menus(menus)]


def configure_submenu(
    submenu_id: str | Iterable[str],
    title: str | None = None,
    *,
    group: str | None = None,
) -> None:
    """Register a configuration for submenu(s).

    Parameters
    ----------
    submenu_id : str or iterable of str
        Submenu ID(s) to configure.
    title : str, optional
        Specify the title of the submenu.
    group : str, optional
        Specify the group ID of the submenu.
    """
    if isinstance(submenu_id, str):
        submenu_id = [submenu_id]
    for sid in submenu_id:
        if title is not None:
            AppActionRegistry.instance()._submenu_titles[sid] = title
        if group is not None:
            AppActionRegistry.instance()._submenu_groups[sid] = group


@overload
def register_function(
    func: None = None,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    types: str | Sequence[str] | None = None,
    enablement: BoolOp | None = None,
    keybindings: Sequence[KeyBindingRule] | None = None,
    run_async: bool = False,
    command_id: str | None = None,
) -> None: ...


@overload
def register_function(
    func: _F,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    types: str | Sequence[str] | None = None,
    enablement: BoolOp | None = None,
    keybindings: Sequence[KeyBindingRule] | None = None,
    run_async: bool = False,
    command_id: str | None = None,
) -> _F: ...


def register_function(
    func=None,
    *,
    menus="plugins",
    title=None,
    types=None,
    enablement=None,
    keybindings=None,
    run_async=False,
    command_id=None,
):
    """
    Register a function as a callback of a plugin action.

    This function can be used either as a decorator or a simple function.

    Parameters
    ----------
    func : callable, optional
        Function to register as an action.
    menus : str or sequence of str, default "plugins"
        Menu(s) to add the action. Submenus are separated by `/`.
    title : str, optional
        Title of the action. Name of the function will be used if not given.
    types: str or sequence of str, optional
        The `type` parameter(s) allowed as the WidgetDataModel. If this parameter
        is given, action will be grayed out if the active window does not satisfy
        the listed types.
    enablement: Expr, optional
        Expression that describes when the action will be enabled. As this argument
        is a generalized version of `types` argument, you cannot use both of them.
    run_async : bool, default False
        If true, the function will be executed asynchronously. Note that if the function
        updates the GUI, running it asynchronously may cause issues.
    command_id : str, optional
        Command ID. If not given, the function qualname will be used.
    """

    def _inner(f: _F) -> _F:
        action = make_action_for_function(
            f,
            menus=menus,
            title=title,
            types=types,
            enablement=enablement,
            keybindings=keybindings,
            run_async=run_async,
            command_id=command_id,
        )
        AppActionRegistry.instance().add_action(action)
        return f

    return _inner if func is None else _inner(func)


def make_action_for_function(
    f: Callable,
    *,
    menus="plugins",
    title=None,
    types=None,
    enablement=None,
    keybindings=None,
    run_async=False,
    command_id=None,
):
    types, enablement, menus = _norm_register_function_args(types, enablement, menus)
    kbs = normalize_keybindings(keybindings)
    if title is None:
        _title = f.__name__.replace("_", " ").title()
    else:
        _title = title
    _enablement = enablement
    if _utils.has_widget_data_model_argument(f):
        _enablement = _expr_and(_enablement, ctx.is_active_window_supports_to_model)

    if inner_widget_class := _utils.get_subwindow_type_arg(f):
        # function is annotated with SubWindow[W]. Use W for enablement.
        widget_id = _utils.get_widget_class_id(inner_widget_class)
        _enablement = _expr_and(_enablement, ctx.active_window_widget_id == widget_id)

    _id = command_id_from_func(f, command_id)
    if isinstance(command_id, str) and ":" in command_id:
        group = command_id.rsplit(":", maxsplit=1)[0]
        menus_normed = _norm_menus_with_group(menus, group)
    else:
        menus_normed = menus
    return Action(
        id=_id,
        title=_title,
        tooltip=tooltip_from_func(f),
        callback=_utils.make_function_callback(
            f, command_id=_id, title=_title, run_async=run_async
        ),
        menus=menus_normed,
        enablement=_enablement,
        keybindings=kbs,
    )


def _expr_and(expr: BoolOp | None, other: BoolOp) -> BoolOp:
    if expr is None:
        return other
    return expr & other


def _norm_register_function_args(
    types: str | Sequence[str] | None,
    enablement: BoolOp | None,
    menus: str | Sequence[str] | None,
) -> tuple[list[str], BoolOp | None, list[str]]:
    if isinstance(types, str):
        _types = [types]
    elif types is None:
        _types = []
    else:
        _types = types
    if len(_types) > 0:
        type_enablement = _types_to_expression(_types)
        if enablement is None:
            enablement = type_enablement
        else:
            enablement = enablement & type_enablement

    # Registered functions that are specific to a certain model type will also be
    # added to the model menu tool button in the top-right corner of the sub window.
    # To efficiently make QModelMenu, the "menus" attribute of each type of function
    # will be reallocated from "/model_menu/XYZ" to "/model_menu:TYPE/XYZ".
    menu_out: list[str] = []
    model_menu_found = False
    pref = "/model_menu"
    reg = AppActionRegistry.instance()
    for menu in norm_menus(menus):
        # if "/model_menu/..." submenu is specified by the user, reallocate it.
        if _is_model_menu_prefix(menu):
            _, _, other = menu.split("/", maxsplit=2)
            _LOGGER.debug("Reallocated: %r ", menu)
            for _type in _types:
                new_place = f"{pref}:{_type}/{other}"
                menu_out.append(new_place)
                _LOGGER.debug("  ---> %r", new_place)
            if menu in reg._submenu_titles:
                _LOGGER.debug("Submenu reallocated: %r ", menu)
                rest = menu[len(pref) :]
                for _type in _types:
                    new_place = f"{pref}:{_type}{rest}"
                    reg._submenu_titles[new_place] = reg._submenu_titles[menu]
                    _LOGGER.debug("  ---> %r", new_place)
            model_menu_found = True
        else:
            menu_out.append(menu)
    if not model_menu_found:
        # if "/model_menu/..." submenu is not specified by the user, they will be added
        # under the root of the model menu.
        for _type in _types:
            new_place = f"{pref}:{_type}"
            menu_out.append(new_place)
            _LOGGER.debug("Menu added: %r", new_place)
    return _types, enablement, menu_out


def _types_to_expression(types: list[str]) -> BoolOp:
    return reduce(operator.or_, map(_type_to_expression, types))


def _type_to_expression(typ: str) -> BoolOp:
    subtypes = typ.split(".")
    nsub = len(subtypes)
    out = ctx.active_window_model_type == subtypes[0]
    if nsub >= 2:
        out &= ctx.active_window_model_subtype_1 == subtypes[1]
        if nsub >= 3:
            out &= ctx.active_window_model_subtype_2 == subtypes[2]
            if nsub >= 4:
                out &= ctx.active_window_model_subtype_3 == subtypes[3]
                if nsub >= 5:
                    raise ValueError(f"The maximum number of subtypes are 4, got {typ}")
    return out


def _is_model_menu_prefix(menu_id: str) -> bool:
    ids = menu_id.split("/")
    if len(ids) < 3:
        return False
    return (ids[0], ids[1]) == ("", "model_menu")


def normalize_keybindings(keybindings):
    if isinstance(keybindings, str):
        kbs = [KeyBindingRule(primary=keybindings)]
    elif isinstance(keybindings, Sequence):
        kbs = []
        for kb in keybindings:
            if isinstance(kb, str):
                kbs.append(KeyBindingRule(primary=kb))
            elif isinstance(kb, Mapping):
                kbs.append(KeyBindingRule(**kb))
            elif isinstance(kb, KeyBindingRule):
                kbs.append(kb)
            else:
                raise TypeError(f"{kb!r} not allowed as a keybinding.")
    elif keybindings is None:
        kbs = keybindings
    else:
        raise TypeError(f"{keybindings!r} not allowed as keybindings.")
    return kbs


def command_id_from_func(func: Callable, command_id: str) -> str:
    """Make a command ID from a function.

    If function `my_func` is defined in a module `my_module`, the command ID will be
    `my_module:my_func`. If `command_id` is given, it will be used instead of `my_func`.
    """
    if command_id is None:
        _id = getattr(func, "__qualname__", str(func))
    else:
        _id = command_id
    return _id


def tooltip_from_func(func: Callable) -> str | None:
    if doc := getattr(func, "__doc__", None):
        tooltip = str(doc)
    else:
        tooltip = None
    return tooltip


@overload
def register_conversion_rule(
    func: _F,
    type_from: str,
    type_to: str,
    *,
    keybindings: KeyBindingsType | None = None,
    command_id: str | None = None,
) -> _F: ...
@overload
def register_conversion_rule(
    type_from: str,
    type_to: str,
    *,
    keybindings: KeyBindingsType | None = None,
    command_id: str | None = None,
) -> Callable[[_F], _F]: ...


def register_conversion_rule(*args, **kwargs):
    """Register a function as a conversion rule."""
    if len(args) == 0:
        no_func = True
    else:
        if isinstance(args[0], str):
            return register_conversion_rule(None, *args, **kwargs)
        no_func = args[0] is None

    def inner(func):
        annot = getattr(func, "__annotations__", {})
        annot.setdefault("return", WidgetDataModel)
        func.__annotations__ = annot
        action = make_conversion_rule(func, *args, **kwargs)
        AppActionRegistry.instance().add_action(action)
        return func

    return inner if no_func else inner(args[0])


def make_conversion_rule(
    func: Callable,
    type_from: str,
    type_to: str,
    *,
    keybindings: KeyBindingsType | None = None,
    command_id: str | None = None,
):
    kbs = normalize_keybindings(keybindings)
    _id = command_id_from_func(func, command_id)
    title = f"Convert {type_from} to {type_to}"
    return Action(
        id=_id,
        title=title,
        tooltip=tooltip_from_func(func),
        callback=_utils.make_function_callback(func, command_id=_id, title=title),
        menus=[{"id": f"/model_menu:{type_from}/convert", "group": "conversion"}],
        enablement=ctx.active_window_model_type == type_from,
        keybindings=kbs,
    )
