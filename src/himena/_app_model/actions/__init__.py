from himena._app_model.actions import (
    file_actions,
    tab_actions,
    window_actions,
    tools_actions,
)  # register actions

from himena._app_model.actions._registry import ACTIONS, SUBMENUS

del file_actions, tab_actions, window_actions, tools_actions

__all__ = ["ACTIONS", "SUBMENUS"]
