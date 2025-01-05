# Define a plugin dock widget.
# The widget is available under the "Myapp" menu.
from himena import new_window
from himena.plugins import register_dock_widget_action

from qtpy import QtWidgets as QtW

@register_dock_widget_action(title="My Widget", area="left")
class MyWidget(QtW.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(["Item 1", "Item 2", "Item 3"])

def main():
    ui = new_window()
    ui.show(run=True)

if __name__ == "__main__":
    main()
