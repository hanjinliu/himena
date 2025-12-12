from pytestqt.qtbot import QtBot
from qtpy import QtWidgets as QtW
from himena.qt.magicgui import get_type_map
from himena.standards.model_meta import TableMeta
from himena.widgets import MainWindow, SubWindow
from himena.utils.table_selection import SelectionType, table_selection_gui_option
from himena.qt._qprogress import QLabeledCircularProgressBar
from himena.qt import QViewBox


def test_table_selection(himena_ui: MainWindow):
    from himena.qt.magicgui import SelectionEdit

    typemap = get_type_map()

    win = himena_ui.add_object(
        [[1, 2], [3, 4], [3, 2]], metadata=TableMeta(selections=[((0, 3), (1, 2))])
    )

    @typemap.magicgui(x=table_selection_gui_option(win))
    def f(x: SelectionType):
        pass

    assert isinstance(f.x, SelectionEdit)
    f.x._read_btn.clicked()
    assert f.x.value == ((0, 3), (1, 2))
    assert f.x._line_edit.value == "0:3, 1:2"

    @typemap.magicgui(
        table={"value": win},
        x=table_selection_gui_option("table"),
    )
    def f(table: SubWindow, x: SelectionType):
        pass


    f.x._read_btn.clicked()
    assert f.x.value == ((0, 3), (1, 2))
    assert f.x._line_edit.value == "0:3, 1:2"

def test_progress_bar(qtbot: QtBot):
    pbar = QLabeledCircularProgressBar("test")
    qtbot.addWidget(pbar)
    pbar.show()
    pbar.pbar().setValue(3)
    assert pbar.pbar().value() == 3
    pbar.pbar().setValue(120)
    pbar.pbar().barWidth()
    pbar.pbar()._on_infinite_timeout()
    pbar.update()
    QtW.QApplication.processEvents()
    pbar._pbar.setInfinite(False)
    pbar.update()
    QtW.QApplication.processEvents()
    pbar._pbar.setInfinite(False)
    pbar.update()
    QtW.QApplication.processEvents()
    pbar._pbar.setInfinite(True)
    pbar.update()
    QtW.QApplication.processEvents()
    pbar._pbar.setInfinite(False)
    pbar.update()
    QtW.QApplication.processEvents()

def test_viewbox(qtbot: QtBot):
    import numpy as np
    from qtpy import QtCore

    class MyViewBox(QViewBox):
        def make_pixmap(self, size: QtCore.QSize) -> np.ndarray:
            arr = np.zeros((size.height(), size.width(), 4), dtype=np.uint8)
            arr[..., 0] = 255  # Red channel
            arr[..., 3] = 255  # Alpha channel
            return arr

    viewbox = MyViewBox()
    qtbot.addWidget(viewbox)
    viewbox.resize(200, 100)
    viewbox.show()
    qtbot.waitForWindowShown(viewbox)
    viewbox.update()
    QtW.QApplication.processEvents()
