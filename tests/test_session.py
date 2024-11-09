from himena import MainWindow
from himena import anchor
from himena.builtins.qt import widgets as _qtw
from pathlib import Path

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
