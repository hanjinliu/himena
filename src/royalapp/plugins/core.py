from __future__ import annotations

from functools import reduce
import operator
from typing import (
    Callable,
    Hashable,
    Mapping,
    Sequence,
    TypeVar,
    cast,
    overload,
    TYPE_CHECKING,
)

from app_model import Action, Application
from app_model.types import SubmenuItem, KeyBindingRule
from app_model.expressions import BoolOp

from royalapp._app_model import AppContext as ctx
from royalapp.types import DockArea, DockAreaString
from royalapp import _utils

if TYPE_CHECKING:
    from royalapp.widgets import MainWindow, DockWidget

    KeyBindingsType = str | KeyBindingRule | Sequence[str] | Sequence[KeyBindingRule]

_F = TypeVar("_F", bound=Callable)


class PluginInterface:
    def __init__(self, place: list[str]):
        self._place = place
        self._actions: list[Action] = []

    def add_child(
        self,
        id: str,
        title: str | None = None,
    ) -> PluginInterface:
        """
        Add a child interface.

        A child menu will be displayed as a submenu of the parent interface.
        """
        if title is None:
            title = id.title()
        return self.__class__(self._place + [id])

    @overload
    def register_function(
        self,
        func: None = None,
        *,
        title: str | None = None,
        types: Hashable | Sequence[Hashable] | None = None,
        enablement: BoolOp | None = None,
        keybindings: Sequence[KeyBindingRule] | None = None,
        command_id: str | None = None,
    ) -> None: ...

    @overload
    def register_function(
        self,
        func: _F,
        *,
        title: str | None = None,
        types: Hashable | Sequence[Hashable] | None = None,
        enablement: BoolOp | None = None,
        keybindings: Sequence[KeyBindingRule] | None = None,
        command_id: str | None = None,
    ) -> _F: ...

    def register_function(
        self,
        func=None,
        *,
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
        title : str, optional
            Title of the action. Name of the function will be used if not given.
        types: hashable or sequence of hashable, optional
            The `type` parameter(s) allowed as the WidgetDataModel. If this parameter
            is given, action will be grayed out if the active window does not satisfy
            the listed types.
        enablement: Expr, optional
            Expression that describes when the action will be enabled. As this argument
            is a generalized version of `types` argument, you cannot use both of them.
        command_id : str, optional
            Command ID. If not given, the function qualname will be used.
        """
        if types is not None:
            if enablement is not None:
                raise TypeError("Cannot give both `types` and `enablement`.")
            elif isinstance(types, Sequence) and not isinstance(types, str):
                enablement = reduce(
                    operator.or_,
                    [ctx.active_window_model_type == hash(t) for t in types],
                )
            else:
                enablement = ctx.active_window_model_type == hash(types)
        kbs = _normalize_keybindings(keybindings)

        def _inner(f: _F) -> _F:
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
            if command_id is None:
                _id = f.__qualname__
            else:
                _id = command_id
            action = Action(
                id=_id,
                title=_title,
                callback=f,
                menus=["/".join(self._place)],
                enablement=_enablement,
                keybindings=kbs,
            )
            self._actions.append(action)
            return f

        return _inner if func is None else _inner(func)

    @overload
    def register_dialog(
        self,
        widget_factory: _F,
        *,
        title: str | None = None,
        types: Hashable | Sequence[Hashable] | None = None,
        enablement: BoolOp | None = None,
        keybindings: Sequence[KeyBindingRule] | None = None,
        command_id: str | None = None,
    ) -> _F: ...

    @overload
    def register_dialog(
        self,
        widget_factory: None = None,
        *,
        title: str | None = None,
        types: Hashable | Sequence[Hashable] | None = None,
        enablement: BoolOp | None = None,
        keybindings: Sequence[KeyBindingRule] | None = None,
        command_id: str | None = None,
    ) -> Callable[[_F], _F]: ...

    def register_dialog(
        self,
        widget_factory=None,
        *,
        title: str | None = None,
        types=None,
        enablement=None,
        keybindings=None,
        command_id=None,
    ):
        def _inner(wf):
            def _exec_dialog(ui: MainWindow):
                widget = wf()
                return ui.add_dialog(widget, title=title)

            return self.register_function(
                _exec_dialog,
                title=title,
                types=types,
                enablement=enablement,
                keybindings=keybindings,
                command_id=command_id,
            )

        return _inner if widget_factory is None else _inner(widget_factory)

    @overload
    def register_dock_widget(
        self,
        widget_factory: _F,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
        keybindings: KeyBindingsType | None = None,
        singleton: bool = False,
        command_id: str | None = None,
    ) -> _F: ...

    @overload
    def register_dock_widget(
        self,
        widget_factory: None = None,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
        keybindings: KeyBindingsType | None = None,
        singleton: bool = False,
        command_id: str | None = None,
    ) -> Callable[[_F], _F]: ...

    def register_dock_widget(
        self,
        widget_factory=None,
        *,
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
            _title = _normalize_title(title, wf)

            def _callback(ui: MainWindow) -> None:
                if singleton:
                    for _backend_dock in ui._dock_widgets:
                        _dock = cast("DockWidget", _backend_dock._royalapp_widget)
                        if id(wf) != _dock._identifier:
                            continue
                        _dock.visible = not _dock.visible
                        return None
                try:
                    widget = wf(ui)
                except TypeError:
                    widget = wf()
                dock = ui.add_dock_widget(
                    widget, title=_title, area=area, allowed_areas=allowed_areas
                )
                dock._identifier = id(wf)
                return None

            if doc := getattr(wf, "__doc__", None):
                tooltip = str(doc)
            else:
                tooltip = None
            if command_id is None:
                _id = getattr(wf, "__qualname__", str(wf))
            else:
                _id = command_id
            action = Action(
                id=_id,
                title=_title,
                tooltip=tooltip,
                callback=_callback,
                menus=["/".join(self._place)],
                category="plugins",
                keybindings=kbs,
            )
            self._actions.append(action)
            return wf

        return _inner if widget_factory is None else _inner(widget_factory)

    @overload
    def register_new_action(
        self,
        func: _F,
        *,
        title: str | None = None,
        keybindings: KeyBindingsType | None = None,
        command_id: str | None = None,
    ) -> _F: ...
    @overload
    def register_new_action(
        self,
        func: None = None,
        *,
        title: str | None = None,
        keybindings: KeyBindingsType | None = None,
        command_id: str | None = None,
    ) -> Callable[[_F], _F]: ...

    def register_new_action(
        self,
        func=None,
        *,
        title=None,
        keybindings=None,
        command_id=None,
    ):
        """
        Register a function as a "New File" action.

        The registered function must provide a `WidgetDataModel` as the return value,
        which is directly passed to the main window to create a new sub-window.

        Parameters
        ----------
        func : callable, optional
            Function that create a `WidgetDataModel` instance.
        title : str, optional
            Title of the window.
        keybindings : keybinding type, optional
            Keybindings to trigger the action.
        command_id : str, optional
            Custom command ID.
        """
        kbs = _normalize_keybindings(keybindings)

        def _inner(f: Callable):
            if doc := getattr(f, "__doc__", None):
                tooltip = str(doc)
            else:
                tooltip = None
            if command_id is None:
                _id = getattr(f, "__qualname__", str(f))
            else:
                _id = command_id
            action = Action(
                id=_id,
                title=_normalize_title(title, f),
                tooltip=tooltip,
                callback=f,
                menus=["file/new"],
                keybindings=kbs,
            )
            self._actions.append(action)
            return f

        return _inner if func is None else _inner(func)

    def install_to(self, app: Application):
        """Installl plugins to the application."""
        existing_menu_ids = set()
        for menu_id, menu in app.menus:
            existing_menu_ids.add(menu_id)
            for each in menu:
                if isinstance(each, SubmenuItem):
                    existing_menu_ids.add(each.submenu)
        app.register_actions(self._actions)
        to_add: list[tuple[str, SubmenuItem]] = []
        for i in range(1, len(self._place)):
            menu_id = "/".join(self._place[:i])
            submenu = "/".join(self._place[: i + 1])
            if submenu in existing_menu_ids:
                continue
            item = SubmenuItem(title=self._place[i], submenu=submenu)
            to_add.append((menu_id, item))
        app.menus.append_menu_items(to_add)


def get_plugin_interface(place: str | list[str] | None = None) -> PluginInterface:
    if place is None:
        place = ["plugins"]
    elif isinstance(place, str):
        place = [place]
    out = PluginInterface(place)
    return out


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
