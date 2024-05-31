from royalapp import new_window
from royalapp.plugins import get_plugin_interface

from qtpy import QtWidgets as QtW

APP_NAME = "myapp"

plugin = get_plugin_interface(APP_NAME)

@plugin.register_dock_widget(title="My Widget", area="left")
class MyWidget(QtW.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(["Item 1", "Item 2", "Item 3"])

def main():
    ui = new_window(APP_NAME)
    ui.show(run=True)

if __name__ == "__main__":
    main()
