from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from app_model import Application
import in_n_out
from himena._app_model._command_registry import CommandsRegistry
from himena.types import WidgetDataModel, FutureInfo, WindowRect

if TYPE_CHECKING:
    from concurrent.futures import Future


def get_model_app(name: str) -> HimenaApplication:
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
        self._dynamic_command_ids: set[str] = set()
        self._futures: set[Future] = set()
        self._attributes: dict[str, object] = {}

    @property
    def attributes(self) -> dict[str, object]:
        """A dictionary of attributes for this application."""
        return self._attributes

    @property
    def commands(self) -> CommandsRegistry:
        """The command registry for this application."""
        return super().commands

    def _future_done_callback(self, f: Future) -> None:
        from himena.widgets import current_instance

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
            if result.update_inplace and info.track and info.track.contexts:
                ui = current_instance()
                ui._process_update_inplace(info.track.contexts, result)
                return None  # no need to process
            elif (top_left := info.top_left) is not None:
                # this clause is used to move the output window to the geometry of
                # preview window or the parametric window.
                _left, _top = top_left
                if info.size is not None:

                    def rov(size):
                        return WindowRect(_left, _top, *info.size)
                else:

                    def rov(size):
                        return WindowRect(_left, _top, *size)

                result.window_rect_override = rov
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
