from himena.plugins import register_dock_widget_action, add_default_status_tip
from himena.consts import MenuId

add_default_status_tip(
    short="full workflow",
    long="The full workflow widget shows the entire workflow tree of the application.",
)


@register_dock_widget_action(
    title="Full Workflow",
    menus=[MenuId.TOOLS_DOCK, MenuId.CORNER],
    area="left",
    singleton=True,
    command_id="builtins:full-workflow",
    icon="clarity:flow-chart-line",
)
def install_command_history(ui):
    """A dock widget that show the full workflow tree in the application."""
    from himena_builtins.qt.full_workflow._widget import QFullWorkflowView

    return QFullWorkflowView(ui)
