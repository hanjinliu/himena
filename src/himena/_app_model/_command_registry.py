from __future__ import annotations
from concurrent.futures import Future
from typing import Any

from psygnal import Signal
from app_model.registries import CommandsRegistry as _CommandsRegistry


class CommandsRegistry(_CommandsRegistry):
    """A command registry that emits signal when command is executed."""

    executed = Signal(str)  # id

    def execute_command(
        self,
        id: str,
        *args: Any,
        execute_asynchronously: bool = False,
        **kwargs: Any,
    ) -> Future:
        result = super().execute_command(
            id,
            *args,
            execute_asynchronously=execute_asynchronously,
            **kwargs,
        )
        self.executed.emit(id)
        return result
