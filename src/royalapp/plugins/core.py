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
    ) -> None: ...

    @overload
    def register_function(
        self,
        func: _F,
        *,
        title: str | None = None,
        types: Hashable | Sequence[Hashable] | None = None,
        enablement: BoolOp | None = None,
    ) -> _F: ...

    def register_function(
        self,
        func=None,
        *,
        title=None,
        types=None,
        enablement=None,
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

            action = Action(
                id=f.__qualname__,
                title=_title,
                callback=f,
                menus=["/".join(self._place)],
                enablement=_enablement,
            )
            self._actions.append(action)

        return _inner if func is None else _inner(func)

    @overload
    def register_dock_widget(
        self,
        widget_factory: _F,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
        keybindings=None,
        singleton: bool = False,
    ) -> _F: ...

    @overload
    def register_dock_widget(
        self,
        widget_factory: None = None,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
        keybindings=None,
        singleton: bool = False,
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
        """
        # Normalize keybindings
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

        def _inner(wf: Callable):
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
                    widget, title=title, area=area, allowed_areas=allowed_areas
                )
                dock._identifier = id(wf)
                return None

            action = Action(
                id=wf.__qualname__,
                title=title,
                callback=_callback,
                menus=["/".join(self._place)],
                category="plugins",
                keybindings=kbs,
            )
            self._actions.append(action)
            return wf

        return _inner if widget_factory is None else _inner(widget_factory)

    def install_to(self, app: Application):
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
