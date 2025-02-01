from himena.plugins import register_dock_widget_action


@register_dock_widget_action(
    title="Image Draw Tool",
    menus=["tools/dock"],
    area="right",
    command_id="builtins:image-draw-tool",
    singleton=True,
)
def make_widget(ui):
    """Open a file explorer widget as a dock widget."""
    from himena_builtins.debug.draw_tool._widget import QImageDrawToolWidget

    return QImageDrawToolWidget(ui)
