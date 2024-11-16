from __future__ import annotations
from typing import Callable

from app_model import Action, Application
from himena._app_model._command_registry import CommandsRegistry


def get_model_app(name: str) -> Application:
    if name in HimenaApplication._instances:
        return HimenaApplication._instances[name]
    return HimenaApplication(name)


class HimenaApplication(Application):
    def __init__(self, name: str):
        super().__init__(name, commands_reg_class=CommandsRegistry)
        self._registered_actions: dict[str, Action] = {}

    def register_actions(self, actions: list[Action]) -> Callable[[], None]:
        disp = super().register_actions(actions)
        for action in actions:
            self._registered_actions[action.id] = action
        return disp

    @property
    def commands(self) -> CommandsRegistry:
        """The command registry for this application."""
        return super().commands
