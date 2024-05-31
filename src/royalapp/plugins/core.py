from __future__ import annotations

from typing import Callable, Hashable, Sequence, TypeVar, overload

from app_model import Application
from app_model.types import SubmenuItem
from app_model.expressions import BoolOp

from royalapp._app_model import AppContext as ctx
from royalapp.widgets import get_application, MainWindow
from royalapp.types import DockArea, DockAreaString
from royalapp import _utils

_F = TypeVar("_F", bound=Callable)


class PluginInterface:
    def __init__(self, app: str | Application, place: list[str]):
        self._app = get_application(app) if isinstance(app, str) else app
        self._place = place
        to_add = []
        for i in range(1, len(self._place)):
            id = "/".join(self._place[:i])
            item = SubmenuItem(
                title=self._place[i], submenu="/".join(self._place[: i + 1])
            )
            to_add.append((id, item))
        self._app.menus.append_menu_items(to_add)

    def add_child(
        self,
        id: str,
        title: str | None = None,
        enablement=None,
    ) -> PluginInterface:
        """
        Add a child interface.

        A child menu will be displayed as a submenu of the parent interface.
        """
        if title is None:
            title = id.title()
        item = SubmenuItem(
            title=title, submenu="/".join(self._place), enablement=enablement
        )
        self._app.menus.append_menu_items([(id, item)])
        return self.__class__(self._app, self._place + [id])

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
            elif isinstance(types, Sequence):
                enablement = ctx.active_window_model_type.in_(types)
            else:
                enablement = ctx.active_window_model_type == types

        def _inner(f: _F) -> _F:
            if title is None:
                _title = f.__name__.replace("_", " ").title()
            else:
                _title = title
            _enablement = enablement
            if annot := _utils.get_widget_data_model_variable(f):
                _expr = ctx.is_active_window_exportable & (
                    ctx.active_window_model_type == annot
                )
                if enablement is None:
                    _enablement = _expr
                else:
                    _enablement = _expr & enablement
            elif _utils.has_widget_data_model_argument(f):
                _expr = ctx.is_active_window_exportable
                if enablement is None:
                    _enablement = _expr
                else:
                    _enablement = _expr & enablement
            self._app.register_action(
                action=f.__qualname__,
                title=_title,
                callback=f,
                menus=["/".join(self._place)],
                enablement=_enablement,
            )

        return _inner if func is None else _inner(func)

    @overload
    def register_dock_widget(
        self,
        widget_factory: _F,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    ) -> _F: ...

    @overload
    def register_dock_widget(
        self,
        widget_factory: None = None,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
    ) -> Callable[[_F], _F]: ...

    def register_dock_widget(
        self,
        widget_factory=None,
        *,
        title: str | None = None,
        area: DockArea | DockAreaString = DockArea.RIGHT,
        allowed_areas: Sequence[DockArea | DockAreaString] | None = None,
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
        """

        def _inner(wf: Callable):
            def _callback(ui: MainWindow):
                ui.add_dock_widget(
                    wf(), title=title, area=area, allowed_areas=allowed_areas
                )

            self._app.register_action(
                action=wf.__qualname__,
                title=title,
                callback=_callback,
                menus=["/".join(self._place)],
            )
            return wf

        return _inner if widget_factory is None else _inner(widget_factory)


def get_plugin_interface(
    app: str, place: str | list[str] | None = None
) -> PluginInterface:
    if not isinstance(app, str):
        raise TypeError(f"`app` must be a string, got {type(app)}.")
    if place is None:
        place = ["Plugins", app]
    out = PluginInterface(app, place)
    return out
