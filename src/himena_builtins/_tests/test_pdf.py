from pathlib import Path
import pytest
from pytestqt.qtbot import QtBot
from himena import MainWindow
from qtpy.QtCore import Qt
from qtpy import QT5

@pytest.mark.skipif(QT5, reason="Qt5 does not implement QtPdfWidgets.")
def test_pdf_viewer(himena_ui: MainWindow, qtbot: QtBot, sample_dir: Path):
    from himena_builtins.qt.widgets.pdf import QPdfViewer

    himena_ui.read_file(sample_dir / "pdf.pdf")
    widget = himena_ui.current_window.widget
    assert isinstance(widget, QPdfViewer)

    widget.control_widget()._spin_box_page.setText("2")
    widget.control_widget()._spin_box_zoom.setText("200")
    qtbot.keyClick(widget, Qt.Key.Key_Plus)
    qtbot.keyClick(widget, Qt.Key.Key_Minus)
