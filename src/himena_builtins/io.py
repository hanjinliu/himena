from __future__ import annotations

from pathlib import Path
from himena.plugins import register_reader_plugin, register_writer_plugin
from himena.data_wrappers import list_installed_dataframe_packages
from himena.types import WidgetDataModel
from himena_builtins import _io
from himena.consts import (
    StandardType,
    BasicTextFileTypes,
    ConventionalTextFileNames,
    ExcelFileTypes,
)


@register_reader_plugin(priority=50)
def read_text(file_path: Path) -> WidgetDataModel:
    if file_path.suffix == ".csv":
        return _io.default_csv_reader(file_path)
    elif file_path.suffix == ".tsv":
        return _io.default_tsv_reader(file_path)
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return _io.default_image_reader(file_path)
    elif file_path.suffix == ".json":
        if file_path.suffixes == [".plot", ".json"]:
            return _io.default_plot_reader(file_path)
        elif file_path.suffixes == [".roi", ".json"]:
            return _io.default_roi_reader(file_path)
        elif file_path.suffixes == [".workflow", ".json"]:
            return _io.default_workflow_reader(file_path)
        else:
            return _io.default_text_reader(file_path)
    elif file_path.suffix in BasicTextFileTypes:
        return _io.default_text_reader(file_path)
    elif file_path.name in ConventionalTextFileNames:
        return _io.default_text_reader(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@read_text.mark_matcher
def _(file_path: Path) -> str | None:
    if file_path.suffix == ".csv":
        return StandardType.TABLE
    elif file_path.suffix == ".tsv":
        return StandardType.TABLE
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return StandardType.IMAGE
    elif file_path.suffix == ".json":
        if file_path.suffixes == [".plot", ".json"]:
            return StandardType.PLOT
        elif file_path.suffixes == [".roi", ".json"]:
            return StandardType.ROIS
        elif file_path.suffixes == [".workflow", ".json"]:
            return StandardType.WORKFLOW
        else:
            return StandardType.TEXT
    elif file_path.suffix in BasicTextFileTypes:
        return StandardType.TEXT
    elif file_path.name in ConventionalTextFileNames:
        return StandardType.TEXT
    return None


@register_reader_plugin(priority=50)
def read_file_list(file_path: Path | list[Path]) -> WidgetDataModel:
    return _io.default_file_list_reader(file_path)


@read_file_list.mark_matcher
def _(file_path: Path | list[Path]) -> str | None:
    if isinstance(file_path, list) or file_path.is_dir():
        return StandardType.MODELS
    return None


@register_reader_plugin(priority=50)
def read_image(file_path: Path) -> WidgetDataModel:
    if file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return _io.default_image_reader(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@read_image.mark_matcher
def _(file_path: Path) -> str | None:
    if file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return StandardType.IMAGE
    return None


@register_reader_plugin(priority=50)
def read_excel(file_path: Path) -> WidgetDataModel:
    if file_path.suffix in ExcelFileTypes:
        return _io.default_excel_reader(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@read_excel.mark_matcher
def _(file_path: Path) -> str | None:
    if file_path.suffix in ExcelFileTypes:
        return StandardType.EXCEL
    return None


@register_reader_plugin(priority=50)
def read_numpy_array(file_path: Path) -> WidgetDataModel:
    if file_path.suffix == ".npy":
        return _io.default_array_reader(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@read_numpy_array.mark_matcher
def _(file_path: Path) -> str | None:
    if file_path.suffix == ".npy":
        return StandardType.ARRAY
    return None


@register_reader_plugin(priority=50)
def read_pickle(file_path: Path) -> WidgetDataModel:
    if file_path.suffix == ".pickle":
        return _io.default_pickle_reader(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@read_pickle.mark_matcher
def _(file_path: Path) -> str | None:
    if file_path.suffix == ".pickle":
        return StandardType.ANY
    return None


@register_reader_plugin(priority=50)
def read_zip(file_path: Path) -> WidgetDataModel:
    if file_path.suffix == ".zip":
        return _io.default_zip_reader(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@read_zip.mark_matcher
def _(file_path: Path) -> str | None:
    if file_path.suffix == ".zip":
        return StandardType.MODELS
    return None


@register_reader_plugin(priority=-100)
def read_as_text_anyway(file_path: Path) -> WidgetDataModel:
    return _io.default_plain_text_reader(file_path)


@read_as_text_anyway.mark_matcher
def _(file_path: Path) -> str | None:
    return StandardType.TEXT


@register_reader_plugin(priority=0)
def read_as_unknown(file_path: Path) -> WidgetDataModel:
    return _io.fallback_reader(file_path)


@read_as_unknown.mark_matcher
def _(file_path: Path) -> str | None:
    return StandardType.READER_NOT_FOUND


@register_reader_plugin(priority=50)
def read_as_pandas_dataframe(file_path: Path) -> WidgetDataModel:
    if file_path.suffix in {".csv", ".txt"}:
        return _io.DataFrameReader("pandas", "read_csv", {})(file_path)
    elif file_path.suffix == ".tsv":
        return _io.DataFrameReader("pandas", "read_csv", {"sep": "\t"})(file_path)
    elif file_path.suffix in {".html", ".htm"}:
        return _io.DataFrameReader("pandas", "read_html", {})(file_path)
    elif file_path.suffix == ".json":
        return _io.DataFrameReader("pandas", "read_json", {})(file_path)
    elif file_path.suffix in {".parquet", ".pq"}:
        return _io.DataFrameReader("pandas", "read_parquet", {})(file_path)
    elif file_path.suffix == ".feather":
        return _io.DataFrameReader("pandas", "read_feather", {})(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@register_reader_plugin(priority=50)
def read_as_polars_dataframe(file_path: Path) -> WidgetDataModel:
    if file_path.suffix in {".csv", ".txt"}:
        return _io.DataFrameReader("polars", "read_csv", {})(file_path)
    elif file_path.suffix == ".tsv":
        return _io.DataFrameReader("polars", "read_csv", {"sep": "\t"})(file_path)
    elif file_path.suffix == ".feather":
        return _io.DataFrameReader("polars", "read_ipc", {})(file_path)
    elif file_path.suffix == ".json":
        return _io.DataFrameReader("polars", "read_json", {})(file_path)
    elif file_path.suffix in {".parquet", ".pq"}:
        return _io.DataFrameReader("polars", "read_parquet", {})(file_path)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


@register_reader_plugin(priority=20)
def read_as_pandas_plot(file_path: Path) -> WidgetDataModel:
    model = read_as_pandas_dataframe(file_path)
    model.type = StandardType.DATAFRAME_PLOT
    return model


@register_reader_plugin(priority=20)
def read_as_polars_plot(file_path: Path) -> WidgetDataModel:
    model = read_as_polars_dataframe(file_path)
    model.type = StandardType.DATAFRAME_PLOT
    return model


@read_as_pandas_dataframe.mark_matcher
@read_as_pandas_plot.mark_matcher
def _(file_path: Path) -> str | None:
    if "pandas" not in list_installed_dataframe_packages():
        return None
    if file_path.suffix in {
        ".csv", ".txt", ".tsv", ".html", ".htm", ".json", ".parquet", ".pq", ".feather",
    }:  # fmt: skip
        return StandardType.DATAFRAME
    return None


@read_as_polars_dataframe.mark_matcher
@read_as_polars_plot.mark_matcher
def _(file_path: Path) -> str | None:
    if "polars" not in list_installed_dataframe_packages():
        return None
    if file_path.suffix in {
        ".csv", ".txt", ".tsv", ".feather", ".json", ".parquet", ".pq",
    }:  # fmt: skip
        return StandardType.DATAFRAME
    return None


@register_writer_plugin(priority=50)
def write_text(model: WidgetDataModel, path: Path):
    return _io.default_text_writer(model, path)


@write_text.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.TEXT) and isinstance(model.value, str)


@register_writer_plugin(priority=50)
def write_table(model: WidgetDataModel, path: Path):
    return _io.default_table_writer(model, path)


@write_table.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.TABLE)


@register_writer_plugin(priority=50)
def write_image(model: WidgetDataModel, path: Path):
    return _io.default_image_writer(model, path)


@write_image.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.IMAGE)


@register_writer_plugin(priority=50)
def write_dict(model: WidgetDataModel, path: Path):
    return _io.default_dict_writer(model, path)


@write_dict.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.DICT)


@register_writer_plugin(priority=50)
def write_excel(model: WidgetDataModel, path: Path):
    return _io.default_excel_writer(model, path)


@write_excel.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.EXCEL)


@register_writer_plugin(priority=50)
def write_array(model: WidgetDataModel, path: Path):
    return _io.default_array_writer(model, path)


@write_array.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.ARRAY)


@register_writer_plugin(priority=50)
def write_plot(model: WidgetDataModel, path: Path):
    return _io.default_plot_writer(model, path)


@write_plot.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.PLOT)


@register_writer_plugin(priority=50)
def write_roi(model: WidgetDataModel, path: Path):
    return _io.default_roi_writer(model, path)


@write_roi.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.ROIS)


@register_writer_plugin(priority=50)
def write_dataframe(model: WidgetDataModel, path: Path):
    return _io.default_dataframe_writer(model, path)


@write_dataframe.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.DATAFRAME)


@register_writer_plugin(priority=50)
def write_models(model: WidgetDataModel, path: Path):
    return _io.default_models_writer(model, path)


@write_models.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.MODELS)


@register_writer_plugin(priority=50)
def write_workflow(model: WidgetDataModel, path: Path):
    return _io.default_workflow_writer(model, path)


@write_workflow.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return model.is_subtype_of(StandardType.WORKFLOW)


@register_writer_plugin(priority=-50)
def write_pickle_anyway(model: WidgetDataModel, path: Path):
    return _io.default_pickle_writer(model, path)


@write_pickle_anyway.mark_matcher
def _(model: WidgetDataModel, path: Path) -> bool:
    return True
