from himena import MainWindow, anchor
from himena.qt import MainWindowQt
from himena.qt._qmain_window import QMainWindow
from himena.builtins.qt import widgets as _qtw
from qtpy.QtCore import Qt
from pathlib import Path
from pytestqt.qtbot import QtBot

def test_type_map_and_session(tmpdir, ui: MainWindow, sample_dir):
    tab0 = ui.add_tab()
    tab0.read_file(sample_dir / "text.txt").update(rect=(30, 40, 120, 150))
    assert type(tab0.current().widget) is _qtw.QDefaultTextEdit
    tab0.read_file(sample_dir / "json.json").update(rect=(150, 40, 250, 150), anchor="top-left")
    assert type(tab0.current().widget) is _qtw.QDefaultTextEdit
    tab1 = ui.add_tab()
    tab1.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="My Image")
    assert type(tab1.current().widget) is _qtw.QDefaultImageView
    tab1.read_file(sample_dir / "html.html").update(rect=(80, 40, 160, 130), title="My HTML")
    # assert type(tab1.current().widget) is _qtw.QDefaultHTMLEdit ?

    session_path = Path(tmpdir) / "test.session.json"
    ui.save_session(session_path)
    ui.clear()
    assert len(ui.tabs) == 0
    ui.read_session(session_path)
    assert len(ui.tabs) == 2
    assert len(ui.tabs[0]) == 2
    assert ui.tabs[0][0].title == "text.txt"
    assert ui.tabs[0][0].rect == (30, 40, 120, 150)
    assert ui.tabs[0][1].title == "json.json"
    assert ui.tabs[0][1].rect == (150, 40, 250, 150)
    assert isinstance(ui.tabs[0][1].anchor, anchor.TopLeftConstAnchor)
    assert len(ui.tabs[1]) == 2
    assert ui.tabs[1][0].title == "My Image"
    assert ui.tabs[1][0].rect == (30, 40, 160, 130)
    assert ui.tabs[1][1].title == "My HTML"
    assert ui.tabs[1][1].rect == (80, 40, 160, 130)

def test_command_palette_events(ui: MainWindowQt, qtbot: QtBot):
    ui.exec_action("show-command-palette")
    qmain: QMainWindow = ui._backend_main_window
    qtbot.add_widget(qmain)
    qline = qmain._command_palette_general._line
    qtbot.keyClick(qline, Qt.Key.Key_O)
    qtbot.keyClick(qline, Qt.Key.Key_Down)
    qtbot.keyClick(qline, Qt.Key.Key_PageDown)
    qtbot.keyClick(qline, Qt.Key.Key_Up)
    qtbot.keyClick(qline, Qt.Key.Key_PageUp)
    qtbot.keyClick(qline, Qt.Key.Key_Escape)
