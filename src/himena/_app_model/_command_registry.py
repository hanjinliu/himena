from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from psygnal import Signal
from app_model.registries import CommandsRegistry as _CommandsRegistry

from himena.types import Cancelled


class CommandsRegistry(_CommandsRegistry):
    """A command registry that emits signal when command is executed."""

    executed = Signal(str, Future)  # id

    def execute_command(
        self,
        id: str,
        *args: Any,
        execute_asynchronously: bool = False,
        **kwargs: Any,
    ) -> Future:
        try:
            cmd = self[id].run_injected
        except KeyError as e:
            raise KeyError(f"Command {id!r} not registered") from e  # pragma: no cover

        if execute_asynchronously:
            with ThreadPoolExecutor() as executor:
                return executor.submit(cmd, *args, **kwargs)

        future: Future = Future()
        try:
            future.set_result(cmd(*args, **kwargs))
        except Cancelled:
            return future  # do not record
        except Exception as e:
            if self._raise_synchronous_exceptions:
                # note, the caller of this function can also achieve this by
                # calling `future.result()` on the returned future object.
                raise e
            future.set_exception(e)

        self.executed.emit(id, future)
        return future
