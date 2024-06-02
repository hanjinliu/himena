from royalapp.plugins import get_plugin_interface

__royalapp_plugin__ = get_plugin_interface(["window"])


@__royalapp_plugin__.register_dock_widget(title="Console", area="bottom")
def install_console(ui):
    from royalapp.builtins.console._widget import QtConsole

    console = QtConsole()
    console.connect_parent(ui)
    return console
