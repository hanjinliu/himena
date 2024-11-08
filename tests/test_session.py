from royalapp import MainWindow
from royalapp import anchor
from pathlib import Path

def test_session(tmpdir, ui: MainWindow, sample_dir):
    tab0 = ui.add_tab()
    tab0.read_file(sample_dir / "text.txt").update(rect=(30, 40, 120, 150))
    tab0.read_file(sample_dir / "json.json").update(rect=(150, 40, 250, 150), anchor="top-left")
    tab1 = ui.add_tab()
    tab1.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="My Image")

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
    assert len(ui.tabs[1]) == 1
    assert ui.tabs[1][0].title == "My Image"
    assert ui.tabs[1][0].rect == (30, 40, 160, 130)
