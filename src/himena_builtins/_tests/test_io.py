import pytest
from pathlib import Path
from himena.consts import StandardType
from himena.io_utils import read, write


@pytest.mark.parametrize(
    "file_name, model_type",
    [
        ("text.txt", StandardType.TEXT),
        ("json.json", StandardType.JSON),
        ("svg.svg", StandardType.SVG),
        ("table.csv", StandardType.TABLE),
        ("table_nonuniform.csv", StandardType.TABLE),
        ("image.png", StandardType.IMAGE),
        ("html.html", StandardType.HTML),
        ("excel.xlsx", StandardType.EXCEL),
        ("array.npy", StandardType.ARRAY),
        ("array_structured.npy", StandardType.ARRAY),
        ("ipynb.ipynb", StandardType.IPYNB),
    ]
)
def test_reading_writing_files(sample_dir: Path, tmpdir, file_name: str, model_type: str):
    tmpdir = Path(tmpdir)
    model = read(sample_dir / file_name)
    assert model.type == model_type
    write(model, tmpdir / file_name)
    model = read(sample_dir / file_name)
    assert model.type == model_type
