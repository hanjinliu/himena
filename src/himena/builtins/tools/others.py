from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.widgets import SubWindow, MainWindow


@register_function(
    types=StandardType.READER_NOT_FOUND,
    menus=[],
    command_id="builtins:open-as-text-anyway",
)
def open_as_text_anyway(ui: MainWindow, win: SubWindow) -> WidgetDataModel[str]:
    """Open as a text file."""
    model = win.to_model()
    if model.type != StandardType.READER_NOT_FOUND:
        raise ValueError(f"Invalid model type: {model.type}")
    out = model.with_value(model.source.read_text(), type=StandardType.TEXT)
    win._close_me(ui)
    return out
