from __future__ import annotations

from functools import reduce, wraps
import operator
import logging
from uuid import uuid4
from typing import (
    Callable,
    Iterator,
    Mapping,
    Sequence,
    TypeVar,
    overload,
    TYPE_CHECKING,
)
import weakref

from app_model import Action, Application
from app_model.types import SubmenuItem, KeyBindingRule, ToggleRule
from app_model.expressions import BoolOp

from himena._app_model import AppContext as ctx
from himena.types import DockArea, DockAreaString
from himena.consts import MenuId, NO_RECORDING_FIELD
from himena import _utils

if TYPE_CHECKING:
    from himena.widgets import MainWindow, DockWidget

    KeyBindingsType = str | KeyBindingRule | Sequence[str] | Sequence[KeyBindingRule]

_F = TypeVar("_F", bound=Callable)
_LOGGER = logging.getLogger(__name__)


class AppActionRegistry:
    _global_instance: AppActionRegistry | None = None

    def __init__(self):
        self._actions: dict[str, Action] = {}
        self._submenu_titles: dict[str, str] = {}
        self._installed_plugins: list[str] = []

    @classmethod
    def instance(cls) -> AppActionRegistry:
        """Get the global instance of the registry."""
        if cls._global_instance is None:
            cls._global_instance = cls()
        return cls._global_instance

    def add_action(self, action: Action) -> None:
        """Add an action to the registry."""
        id_ = action.id
        if id_ in self._actions:
            raise ValueError(f"Action ID {id_} already exists.")
        self._actions[id_] = action

    @property
    def installed_plugins(self) -> list[str]:
        return self._installed_plugins

    def iter_actions(self, app: Application) -> Iterator[Action]:
        for id_, action in self._actions.items():
            if id_ not in app.commands:
                yield action

    def submenu_title(self, id: str) -> str:
        if title := self._submenu_titles.get(id):
            return title
        return id.split("/")[-1].title()

    @property
    def submenu_titles(self) -> dict[str, str]:
        return self._submenu_titles

    def install_to(
        self,
        app: Application,
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
        existing_menu_ids = {_id.value for _id in MenuId}
        for menu_id, menu in app.menus:
            existing_menu_ids.add(menu_id)
            for each in menu:
                if isinstance(each, SubmenuItem):
                    existing_menu_ids.add(each.submenu)

        added_menu_ids = _utils.OrderedSet[str]()
        for action in actions:
            if action.menus is not None:
                ids = [a.id for a in action.menus]
                added_menu_ids.update(ids)
        app.register_actions(actions)

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
                _LOGGER.info("Adding submenu: %s", submenu)
                title = self.submenu_title(submenu)
                item = SubmenuItem(title=title, submenu=submenu)
                to_add.append((menu_id, item))

        app.menus.append_menu_items(to_add)
        return new_menu_ids


def _norm_menus(menus: str | Sequence[str]) -> list[str]:
    if isinstance(menus, str):
        return [menus]
    return list(menus)


def configure_submenu(submenu_id: str, title: str) -> None:
    """Register a title for a submenu."""
    AppActionRegistry.instance()._submenu_titles[submenu_id] = title


@overload
def register_function(
    func: None = None,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    types: str | Sequence[str] | None = None,
    enablement: BoolOp | None = None,
    keybindings: Sequence[KeyBindingRule] | None = None,
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
    command_id=None,
):
    types, enablement, menus = _norm_register_function_args(types, enablement, menus)
    kbs = _normalize_keybindings(keybindings)
    if title is None:
        _title = f.__name__.replace("_", " ").title()
    else:
        _title = title
    _enablement = enablement
    if _utils.has_widget_data_model_argument(f):
        _expr = ctx.is_active_window_exportable
        if enablement is None:
            _enablement = _expr
        else:
            _enablement = _expr & enablement
    _id = _command_id_from_func(f, command_id)
    return Action(
        id=_id,
        title=_title,
        tooltip=_tooltip_from_func(f),
        callback=_utils.make_function_callback(f, command_id=_id),
        menus=_norm_menus(menus),
        enablement=_enablement,
        keybindings=kbs,
    )


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
    for menu in _norm_menus(menus):
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


@overload
def register_dock_widget(
    widget_factory: _F,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings: KeyBindingsType | None = None,
    singleton: bool = False,
    command_id: str | None = None,
) -> _F: ...


@overload
def register_dock_widget(
    widget_factory: None = None,
    *,
    menus: str | Sequence[str] = "plugins",
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings: KeyBindingsType | None = None,
    singleton: bool = False,
    command_id: str | None = None,
) -> Callable[[_F], _F]: ...


def register_dock_widget(
    widget_factory=None,
    *,
    menus="plugins",
    title: str | None = None,
    area: DockArea | DockAreaString = DockArea.RIGHT,
    allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    keybindings=None,
    singleton: bool = False,
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
    command_id : str, optional
        Command ID. If not given, the function name will be used.
    """
    kbs = _normalize_keybindings(keybindings)

    def _inner(wf: Callable):
        _callback = DockWidgetCallback(
            wf,
            title=title,
            area=area,
            allowed_areas=allowed_areas,
            singleton=singleton,
            uuid=uuid4().int,
        )
        if singleton:
            toggle_rule = ToggleRule(get_current=_callback.widget_visible)
        else:
            toggle_rule = None
        action = Action(
            id=_command_id_from_func(wf, command_id),
            title=_callback._title,
            tooltip=_tooltip_from_func(wf),
            callback=_callback,
            menus=_norm_menus(menus),
            keybindings=kbs,
            toggled=toggle_rule,
        )
        AppActionRegistry.instance().add_action(action)
        return wf

    return _inner if widget_factory is None else _inner(widget_factory)


class DockWidgetCallback:
    """Callback for registering dock widgets."""

    def __init__(
        self,
        func: Callable,
        title: str | None,
        area: DockArea | DockAreaString,
        allowed_areas: Sequence[DockArea | DockAreaString] | None,
        singleton: bool,
        uuid: int | None,
    ):
        self._func = func
        self._title = _normalize_title(title, func)
        self._area = area
        self._allowed_areas = allowed_areas
        self._singleton = singleton
        self._uuid = uuid
        self._widget_ref: Callable[[], None | DockWidget] = lambda: None
        wraps(func)(self)
        self.__annotations__ = {"ui": "MainWindow"}
        setattr(self, NO_RECORDING_FIELD, True)  # showing dock widget is not recorded

    def __call__(self, ui: MainWindow) -> None:
        if self._singleton:
            if _dock := ui.dock_widgets.widget_for_id(self._uuid):
                _dock.visible = not _dock.visible
                return None
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
        self._widget_ref = weakref.ref(dock)
        return None

    def widget_visible(self) -> bool:
        if widget := self._widget_ref():
            return widget.visible
        return False


def _normalize_keybindings(keybindings):
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


def _normalize_title(title: str | None, func: Callable) -> str:
    if title is None:
        return func.__name__.replace("_", " ").title()
    return title


def _command_id_from_func(func: Callable, command_id: str) -> str:
    """Make a command ID from a function.

    If function `my_func` is defined in a module `my_module`, the command ID will be
    `my_module:my_func`. If `command_id` is given, it will be used instead of `my_func`.
    """
    if command_id is None:
        _id = getattr(func, "__qualname__", str(func))
    else:
        if command_id.count(":") != 1:
            raise ValueError(
                "command_id must be in the format of 'module:function_name'.",
            )
        _id = command_id
    return _id


def _tooltip_from_func(func: Callable) -> str | None:
    if doc := getattr(func, "__doc__", None):
        tooltip = str(doc)
    else:
        tooltip = None
    return tooltip
