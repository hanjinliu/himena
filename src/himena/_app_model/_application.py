from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from app_model import Action, Application
import in_n_out
from himena._app_model._command_registry import CommandsRegistry
from himena.types import WidgetDataModel, FutureInfo, WindowRect

if TYPE_CHECKING:
    from concurrent.futures import Future


def get_model_app(name: str) -> Application:
    if name in HimenaApplication._instances:
        return HimenaApplication._instances[name]
    return HimenaApplication(name)


class HimenaApplication(Application):
    """The Application class for Himena."""

    def __init__(self, name: str):
        super().__init__(
            name,
            commands_reg_class=CommandsRegistry,
            injection_store_class=HimenaInjectionStore,
            raise_synchronous_exceptions=True,
        )
        self._registered_actions: dict[str, Action] = {}
        self._dynamic_command_ids: set[str] = set()
        self._futures: set[Future] = set()

    def register_actions(self, actions: list[Action]) -> Callable[[], None]:
        actions = list(actions)
        disp = super().register_actions(actions)
        for action in actions:
            self._registered_actions[action.id] = action
        return disp

    @property
    def commands(self) -> CommandsRegistry:
        """The command registry for this application."""
        return super().commands

    def _future_done_callback(self, f: Future) -> None:
        self._futures.discard(f)
        if f.cancelled():
            return
        result = f.result()
        if info := FutureInfo.get(f):
            type_hint = info.type_hint
        else:
            type_hint = None
        if isinstance(result, WidgetDataModel) and info is not None:
            if info.track is not None and len(result.workflow) == 0:
                result.workflow = info.track.to_workflow(info.kwargs)
            # this clause is used to move the output window to the geometry of preview
            # window or the parametric window.
            if (top_left := info.top_left) is not None:
                _left, _top = top_left
                if info.size is not None:
                    result.window_rect_override = lambda _: WindowRect(
                        _left, _top, *info.size
                    )
                else:
                    result.window_rect_override = lambda size: WindowRect(
                        _left, _top, *size
                    )
        self.injection_store.process(result, type_hint=type_hint)


class HimenaInjectionStore(in_n_out.Store):
    def process(
        self,
        result,
        *,
        type_hint: object | None = None,
        first_processor_only: bool = False,
        raise_exception: bool = True,  # update default
        _funcname: str = "",
    ) -> None:
        super().process(
            result, type_hint=type_hint, first_processor_only=first_processor_only,
            raise_exception=raise_exception, _funcname=_funcname
        )  # fmt: skip

    def inject_processors(self, *args, **kwargs) -> Callable:
        kwargs["raise_exception"] = True
        return super().inject_processors(*args, **kwargs)
