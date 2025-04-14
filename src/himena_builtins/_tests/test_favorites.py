from qtpy import QtCore
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena.plugins import update_config_context
from himena_builtins.qt.favorites._widget import QFavoriteCommands, QCommandPushButton
from himena_builtins.qt.favorites import FavoriteCommandsConfig

def test_favorite_commands_widget(qtbot: QtBot, himena_ui: MainWindow):
    widget = QFavoriteCommands(himena_ui)
    qtbot.addWidget(widget)
    himena_ui.exec_action("builtins:favorite-commands")
    mime = QtCore.QMimeData()
    mime.setData("text/command-id", b"new-tab")
    assert widget._command_list.count() == 0

    # dropping a new command
    widget._command_list._drop_mime_data(mime)
    assert widget._command_list.count() == 1

    # dropping the existing command should not add a new one
    widget._command_list._drop_mime_data(mime)
    assert widget._command_list.count() == 1

    item = widget._command_list.item(0)
    btn = widget._command_list.itemWidget(item)
    assert isinstance(btn, QCommandPushButton)
    btn._make_context_menu()
    cfg = himena_ui.app_profile.plugin_configs["builtins:favorite-commands"]
    assert cfg["commands"]["value"] == ["new-tab"]

    with update_config_context(FavoriteCommandsConfig, update_widget=True) as cfg:
        cfg.commands = ["close-tab"]
