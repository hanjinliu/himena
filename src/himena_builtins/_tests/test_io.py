import pytest
from pathlib import Path
from himena.consts import StandardType
from himena.io_utils import read, write
from himena.standards import roi
from himena.types import WidgetDataModel
from himena_builtins.tools.others import show_statistics, show_metadata
from himena_builtins.io import read_as_pandas_dataframe, read_as_polars_dataframe, read_as_text_anyway

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
    show_statistics(model)
    show_metadata(model)

def test_dataframe(sample_dir: Path, tmpdir):
    tmpdir = Path(tmpdir)
    model = read(sample_dir / "pq.parquet")
    assert model.type == StandardType.DATAFRAME
    write(model, tmpdir / "pq.parquet")
    model = read(sample_dir / "pq.parquet")
    assert model.type == StandardType.DATAFRAME
    show_statistics(model)
    show_metadata(model)

def test_pandas_io(tmpdir):
    import pandas as pd

    df = pd.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
    save_dir = Path(tmpdir)
    df.to_csv(save_dir / "test.csv", index=False)
    read_as_pandas_dataframe(save_dir / "test.csv")
    df.to_csv(save_dir / "test.tsv", index=False, sep="\t")
    read_as_pandas_dataframe(save_dir / "test.tsv")
    df.to_json(save_dir / "test.json", index=False)
    read_as_pandas_dataframe(save_dir / "test.json")
    df.to_parquet(save_dir / "test.parquet", index=False)
    read_as_pandas_dataframe(save_dir / "test.parquet")
    df.to_feather(save_dir / "test.feather")
    read_as_pandas_dataframe(save_dir / "test.feather")

def test_polars_io(tmpdir):
    import polars as pl

    df = pl.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
    save_dir = Path(tmpdir)
    df.write_csv(save_dir / "test.csv")
    read_as_polars_dataframe(save_dir / "test.csv")
    df.write_csv(save_dir / "test.tsv", separator="\t")
    read_as_polars_dataframe(save_dir / "test.tsv")
    df.write_parquet(save_dir / "test.parquet")
    read_as_polars_dataframe(save_dir / "test.parquet")
    df.write_json(save_dir / "test.json")
    read_as_polars_dataframe(save_dir / "test.json")
    df.write_ipc(save_dir / "test.feather")
    read_as_polars_dataframe(save_dir / "test.feather")

def test_read_as_text_anyway(tmpdir):
    text = "This is a test."
    file_path = Path(tmpdir, "test.xxx")
    file_path.write_text(text)
    result = read_as_text_anyway(file_path)
    assert result.value == text

def test_roi_reader(tmpdir):
    file_path = Path(tmpdir, "roi.roi")
    roi_list = roi.RoiListModel(
        items=[
            roi.RectangleRoi(x=1, y=2, width=3, height=4),
            roi.EllipseRoi(x=5, y=6, width=7, height=8),
        ]
    )
    write(WidgetDataModel(value=roi_list, type=StandardType.ROIS), file_path)
    read(file_path)
