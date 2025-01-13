from himena import MainWindow
from himena.types import Margins
from magicgui import widgets as mgw
from qtpy.QtWidgets import QApplication

def test_layout_1d(himena_ui: MainWindow):
    tab = himena_ui.add_tab()
    vlayout = tab.add_vbox_layout(margins=(2, 2, 3, 2))
    win0 = tab.add_widget(mgw.Label(value="label 0"))
    win1 = tab.add_widget(mgw.Label(value="label 1"))
    win2 = tab.add_widget(mgw.Label(value="label 2"))
    vlayout.add(win0)
    hlayout = vlayout.add_hbox_layout(spacing=3)
    hlayout.add(win1, win2)
    assert vlayout.margins == Margins(2, 2, 3, 2)
    assert vlayout.spacing == 0
    assert hlayout.margins == Margins(0, 0, 0, 0)
    assert hlayout.spacing == 3
    himena_ui.size = (500, 500)
    QApplication.processEvents()
    himena_ui.size = (600, 400)
    QApplication.processEvents()

    del hlayout[1]
    himena_ui.size = (500, 500)
    QApplication.processEvents()
    himena_ui.size = (600, 400)
    QApplication.processEvents()
