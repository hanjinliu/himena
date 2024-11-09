from typing import Callable
from app_model.types import KeyBindingRule, KeyCode, KeyMod
import json
from himena.consts import MenuId, StandardTypes
from himena.types import Parametric, WidgetDataModel, TextFileMeta
from himena.widgets import MainWindow
from himena._app_model.actions._registry import ACTIONS, SUBMENUS
from himena._app_model._context import AppContext as _ctx


CMD_GROUP = "command-palette"


@ACTIONS.append_from_fn(
    id="show-command-palette",
    title="Command palette",
    icon="material-symbols:palette-outline",
    menus=[
        {"id": MenuId.TOOLS, "group": CMD_GROUP},
        {"id": MenuId.TOOLBAR, "group": CMD_GROUP},
    ],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyP)],
)
def show_command_palette(ui: MainWindow) -> None:
    """Open the command palette."""
    ui._backend_main_window._show_command_palette("general")


@ACTIONS.append_from_fn(
    id="go-to-window",
    title="Go to window ...",
    icon="gg:enter",
    menus=[
        {"id": MenuId.TOOLS, "group": CMD_GROUP},
        {"id": MenuId.TOOLBAR, "group": CMD_GROUP},
    ],
    enablement=_ctx.has_tabs,
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyG)],
)
def go_to_window(ui: MainWindow) -> None:
    """Go to an existing window."""
    ui._backend_main_window._show_command_palette("goto")


@ACTIONS.append_from_fn(
    id="filter-text",
    title="Filter text ...",
    menus=[MenuId.TOOLS_TEXT],
    enablement=_ctx.active_window_model_type == StandardTypes.TEXT,
    need_function_callback=True,
)
def filter_text(model: WidgetDataModel[str]) -> Parametric[str]:
    """Go to an existing window."""

    def filter_text_data(include: str = "", exclude: str = "") -> WidgetDataModel[str]:
        if include == "":
            _include = _const_func(True)
        else:
            _include = _contains_func(include)
        if exclude == "":
            _exclude = _const_func(False)
        else:
            _exclude = _contains_func(exclude)
        new_text = "\n".join(
            line
            for line in model.value.splitlines()
            if _include(line) and not _exclude(line)
        )
        return WidgetDataModel(
            value=new_text,
            type=model.type,
            title=f"{model.title} (filtered)",
            extensions=model.extensions,
            additional_data=model.additional_data,
        )

    return filter_text_data


SUBMENUS.append_from(MenuId.TOOLS, MenuId.TOOLS_TEXT, title="Text")


@ACTIONS.append_from_fn(
    id="format-json",
    title="Format JSON ...",
    menus=[MenuId.TOOLS_TEXT],
    enablement=_ctx.active_window_model_type == StandardTypes.TEXT,
    need_function_callback=True,
)
def format_json(model: WidgetDataModel) -> Parametric:
    """Format JSON."""

    def format_json_data(indent: int = 2) -> WidgetDataModel[str]:
        return WidgetDataModel(
            value=json.dumps(json.loads(model.value), indent=indent),
            type=model.type,
            title=f"{model.title} (formatted)",
            extension_default=".json",
            extensions=model.extensions,
            additional_data=TextFileMeta(language="JSON", spaces=indent),
        )

    return format_json_data


def _const_func(x) -> Callable[[str], bool]:
    def _func(line: str):
        return x

    return _func


def _contains_func(x) -> Callable[[str], bool]:
    def _func(line: str):
        return x in line

    return _func
