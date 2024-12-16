from pathlib import Path
from himena import MainWindow
from himena.types import LocalReaderMethod
from himena.consts import StandardType

def test_reading_files(ui: MainWindow, sample_dir: Path):
    tab0 = ui.add_tab()
    win = tab0.read_file(sample_dir / "text.txt")
    assert win.model_type() == StandardType.TEXT
    win = tab0.read_file(sample_dir / "json.json")
    assert win.model_type() == StandardType.JSON
    win = tab0.read_file(sample_dir / "svg.svg")
    assert win.model_type() == StandardType.SVG
    win = tab0.read_file(sample_dir / "table.csv")
    assert win.model_type() == StandardType.TABLE
    assert isinstance(method := win.to_model().method, LocalReaderMethod)
    assert method.plugin == "himena_builtins.io.default_reader_provider"
    # win = tab0.read_file(sample_dir / "table.csv", plugin="builtin:")
    win = tab0.read_file(sample_dir / "image.png")
    assert win.model_type() == StandardType.IMAGE
    win = tab0.read_file(sample_dir / "html.html")
    assert win.model_type() == StandardType.HTML
    win = tab0.read_file(sample_dir / "excel.xlsx")
    assert win.model_type() == StandardType.EXCEL
    win = tab0.read_file(sample_dir / "array.npy")
    assert win.model_type() == StandardType.ARRAY

def test_reading_file_group(ui: MainWindow, sample_dir: Path):
    tab0 = ui.add_tab()
    win = tab0.read_file(
        [
            sample_dir / "text.txt",
            sample_dir / "json.json",
            sample_dir / "table.csv",
        ]
    )
