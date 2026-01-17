from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, Any, Mapping

from cmap import Color, Colormap
import numpy as np
from numpy.typing import NDArray
from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from himena import MainWindow
from himena.consts import StandardType
from himena.types import Size, WidgetDataModel, Parametric
from himena.standards import plotting as hplt, roi as _roi
from himena.standards.model_meta import DataFrameMeta, TableMeta, DataFramePlotMeta
from himena.utils.collections import UndoRedoStack
from himena.utils import proxy
from himena.plugins import validate_protocol, register_function, config_field
from himena.data_wrappers import wrap_dataframe, DataFrameWrapper
from himena_builtins.qt.widgets._table_components import (
    QTableBase,
    QSelectionRangeEdit,
    format_table_value,
    QDraggableHorizontalHeader,
    QToolButtonGroup,
    Editability,
    FLAGS,
    parse_string,
)
from himena_builtins.qt.widgets._splitter import QSplitterHandle
from himena_builtins.qt.widgets._shared import spacer_widget, index_contains

if TYPE_CHECKING:
    from himena_builtins.qt.widgets._table_components._selection_model import Index

    _Index = int | slice | NDArray[np.integer]


class QDataFrameModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, df: DataFrameWrapper, transpose: bool = False, parent=None):
        super().__init__(parent)
        self._df = df
        self._transpose = transpose
        self._cfg = DataFrameConfigs()
        self._proxy: proxy.TableProxy = proxy.IdentityProxy()

    @property
    def df(self) -> DataFrameWrapper:
        return self._df

    def rowCount(self, parent=None):
        if self._transpose:
            return self.df.num_columns()
        return self.df.num_rows()

    def columnCount(self, parent=None):
        if self._transpose:
            return self.df.num_rows()
        return self.df.num_columns()

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if self._transpose:
            r, c = index.column(), index.row()
        else:
            r, c = index.row(), index.column()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            df = self.df
            if r < df.num_rows() and c < df.num_columns():
                r1 = self._proxy.map(r)
                value = df[r1, c]
                dtype = df.get_dtype(c)
                if role == Qt.ItemDataRole.DisplayRole:
                    text = format_table_value(value, dtype.kind)
                else:
                    text = str(value)
                return text
        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            r0, c0 = index.row(), index.column()
            value_parsed = parse_string(value, self.df.get_dtype(c0).kind)
            arr = np.array([value_parsed])
            cname = self.df.column_names()[c0]
            self.parent().dataframe_update((r0, c0), wrap_dataframe({cname: arr}))
            return True
        return False

    def flags(self, index):
        return FLAGS

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if self._transpose:
            is_header = orientation == Qt.Orientation.Vertical
        else:
            is_header = orientation == Qt.Orientation.Horizontal
        if is_header:
            if role == Qt.ItemDataRole.DisplayRole:
                if section >= self.df.num_columns():
                    return None
                return str(self.df.column_names()[section])
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.num_columns():
                    return self._column_tooltip(section)
                return None

        else:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section)

    def _column_tooltip(self, section: int):
        name = self.df.column_names()[section]
        dtype = self.df.get_dtype(section)
        return f"{name} (dtype: {dtype.name})"

    if TYPE_CHECKING:

        def parent(self) -> QDataFrameView: ...


class QDataFrameView(QTableBase):
    """A table widget for viewing DataFrame.

    ## Basic Usage

    - This widget is a table widget for viewing a dataframe. Supported data types
      includes `dict[str, numpy.ndarray]`, `pandas.DataFrame`, `polars.DataFrame`,
      `pyarrow.Table` and `narwhals.DataFrame`.
    - `Ctrl+F` to search a string in the table.
    - Each item can be edited by double-clicking it, but only the standard scalar types
      are supported.

    ## Drag and Drop

    Selected columns can be dragged out as a model of type `StandardType.DATAFRAME`
    ("dataframe"). Use the drag indicator on the header to start dragging.
    """

    __himena_widget_id__ = "builtins:QDataFrameView"
    __himena_display_name__ = "Built-in DataFrame Viewer"

    def __init__(self, ui: MainWindow):
        super().__init__(ui)
        self._hor_header = QDraggableHorizontalHeader(self)
        self.setHorizontalHeader(self._hor_header)
        self.horizontalHeader().setFixedHeight(18)
        self.horizontalHeader().setDefaultSectionSize(75)
        self._control: QDataFrameViewControl | None = None  # deferred
        self._model_type = StandardType.DATAFRAME
        self._undo_stack = UndoRedoStack[EditAction](size=20)
        self._sep_on_copy = "\t"
        self._extension_default = ".csv"
        self.set_editable(False)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        df = wrap_dataframe(model.value)
        transpose = False
        if isinstance(meta := model.metadata, DataFrameMeta):
            transpose = meta.transpose
        self.setModel(QDataFrameModel(df, transpose=transpose, parent=self))
        if df.num_rows() == 1 and transpose:
            # single-row, row-orinted table should be expanded
            self.resizeColumnsToContents()
        if ext := model.extension_default:
            self._extension_default = ext
        # update the table-widget-specific settings
        if isinstance(meta := model.metadata, TableMeta):
            self._selection_model.clear()
            if (pos := meta.current_position) is not None:
                index = self.model().index(*pos)
                self.setCurrentIndex(index)
                self._selection_model.current_index = pos
            for (r0, r1), (c0, c1) in meta.selections:
                self._selection_model.append((slice(r0, r1), slice(c0, c1)))

        self.control_widget().update_for_table(self)
        self._model_type = model.type
        self._undo_stack.clear()
        self.update()

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        # NOTE: if this model is passed to another widget and modified in this widget,
        # the other dataframe will be modified as well. To avoid this, we need to reset
        # the copy-on-write state of this array.
        return WidgetDataModel(
            value=self.model().df.unwrap(),
            type=self.model_type(),
            extension_default=self._extension_default,
            metadata=self._prep_table_meta(cls=DataFrameMeta),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def theme_changed_callback(self, theme):
        if self._control is not None:
            self._control.update_theme(theme)

    @validate_protocol
    def update_configs(self, cfg: DataFrameConfigs):
        self._sep_on_copy = cfg.separator_on_copy.encode().decode("unicode_escape")
        self._hor_header._drag_enabled = cfg.column_drag_enabled

    @validate_protocol
    def is_modified(self) -> bool:
        if self._modified_override is not None:
            return self._modified_override
        return self._undo_stack.undoable()

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        self._modified_override = value

    @validate_protocol
    def is_editable(self) -> bool:
        return self.editTriggers() == Editability.TRUE

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        if value:
            trig = Editability.TRUE
        else:
            trig = Editability.FALSE
        self.setEditTriggers(trig)

    @validate_protocol
    def control_widget(self) -> QDataFrameViewControl:
        if self._control is None:
            self._control = QDataFrameViewControl(self)
        return self._control

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        _ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        _shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if _ctrl and e.key() == QtCore.Qt.Key.Key_C:
            return self.copy_data(header=_shift)
        elif _ctrl and e.key() == QtCore.Qt.Key.Key_V:
            return self._paste_from_clipboard()
        elif _ctrl and e.key() == QtCore.Qt.Key.Key_F:
            return self._find_string()
        elif _ctrl and e.key() == QtCore.Qt.Key.Key_Z:
            return self.undo()
        elif _ctrl and e.key() == QtCore.Qt.Key.Key_Y:
            return self.redo()
        return super().keyPressEvent(e)

    def undo(self):
        """Undo the last action."""
        if action := self._undo_stack.undo():
            action.invert().apply(self)
            self.update()

    def redo(self):
        """Redo the last undone action."""
        if action := self._undo_stack.redo():
            action.apply(self)
            self.update()

    def edit_cell(self, r: int, c: int, value: str):
        """Emulate editing an item at (r, c) with the given string value."""
        idx = self.model().index(r, c)
        self.model().setData(idx, value, Qt.ItemDataRole.EditRole)
        # datChanged needs to be emitted manually
        self.model().dataChanged.emit(idx, idx, [Qt.ItemDataRole.EditRole])

    def copy_data(self, header: bool = False):
        rng = self._selection_model.get_single_range()

        r, c = rng
        r1 = self._map_row_index(r)
        csv_text = self.model().df.get_subset(r1, c).to_csv_string("\t", header=header)
        if clipboard := QtGui.QGuiApplication.clipboard():
            clipboard.setText(csv_text)

    def _paste_from_clipboard(self):
        if clipboard := QtGui.QGuiApplication.clipboard():
            self.paste_data(clipboard.text())

    def paste_data(self, text: str):
        """Paste a text data to the selected cells."""
        if not text:
            return
        buf = StringIO(text)
        arr_paste = np.loadtxt(
            buf, dtype=np.dtypes.StringDType(), delimiter="\t", ndmin=2
        )
        if cur_range := self._selection_model.current_range:
            rsl, csl = cur_range
        else:
            raise ValueError("No selection to paste data into.")
        r0, r1 = rsl.start, rsl.stop
        c0, c1 = csl.start, csl.stop
        if r1 - r0 == 1 and c1 - c0 == 1:
            # single cell selected, expand to fit the pasted data
            r1 = r0 + arr_paste.shape[0]
            c1 = c0 + arr_paste.shape[1]
            self._selection_model.clear()
            self._selection_model.append((slice(r0, r1), slice(c0, c1)))
        elif arr_paste.shape == (1, 1):
            arr_paste = np.full(
                (r1 - r0, c1 - c0), arr_paste[0, 0], dtype=arr_paste.dtype
            )
            r1 = r0 + arr_paste.shape[0]
            c1 = c0 + arr_paste.shape[1]
        elif arr_paste.shape != (r1 - r0, c1 - c0):
            raise ValueError(
                f"Pasted data shape {arr_paste.shape} does not match selection shape {(r1 - r0, c1 - c0)}."
            )
        columns = self.model().df.column_names()
        df_paste = {}
        for ci in range(c0, c1):
            col_name = columns[ci]
            dtype_kind = self.model().df.get_dtype(ci).kind
            df_paste[col_name] = [
                parse_string(each, dtype_kind) for each in arr_paste[:, ci - c0]
            ]

        self.dataframe_update((slice(r0, r1), slice(c0, c1)), wrap_dataframe(df_paste))
        self.update()

    def dataframe_update(
        self,
        index: tuple[_Index, _Index],
        df: DataFrameWrapper,
        record_undo: bool = True,
    ):
        r, c = index
        r1 = self._map_row_index(r)
        _model = self.model()
        if isinstance(r1, int | np.integer):
            r1 = slice(r1, r1 + 1)
        if isinstance(c, slice):
            crange = range(c.start, c.stop)
            csl = c
        elif isinstance(c, np.ndarray):
            crange = c
            csl = c
        else:
            crange = [c]
            csl = slice(c, c + 1)
        old = _model.df.get_subset(r1, csl).copy()

        column_names = _model.df.column_names()
        _df_updated = _model.df
        for i_col in crange:
            name = column_names[i_col]
            target = _model.df.column_to_array(name).copy()
            target[r1] = df.column_to_array(name)
            _df_updated = _df_updated.with_columns({name: target})
        new = _df_updated.get_subset(r1, csl).copy()
        _model._df = _df_updated
        if isinstance(prx := self._table_proxy(), proxy.SortProxy) and index_contains(
            prx.index, c
        ):
            self._recalculate_proxy()
        if record_undo:
            self._undo_stack.push(EditAction(old, new, index))

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Copy", self.copy_data)
        menu.addAction("Copy With Header", lambda: self.copy_data(header=True))
        action = menu.addAction("Paste", self._paste_from_clipboard)
        action.setEnabled(self.is_editable())
        return menu

    def _auto_resize_columns(self):
        """Resize all the columns."""
        self.resizeColumnsToContents()

    def _sort_table_by_column(self):
        """Sort the table by the current column."""
        if self.model()._transpose:
            raise NotImplementedError("Sorting is not supported for transposed table.")
        if selected_cols := self._get_selected_cols():
            c = min(selected_cols)
            model = self.model()
            if isinstance(model._proxy, proxy.IdentityProxy):
                model._proxy = proxy.SortProxy.from_dataframe(c, model.df)
            elif isinstance(pxy := model._proxy, proxy.SortProxy):
                if c != pxy.index:
                    model._proxy = proxy.SortProxy.from_dataframe(c, model.df)
                elif pxy._ascending:
                    model._proxy = pxy.switch_ascending()
                else:
                    model._proxy = proxy.IdentityProxy()
            else:
                model._proxy = proxy.IdentityProxy()
            self.update()

    def _table_proxy(self) -> proxy.TableProxy:
        return self.model()._proxy

    def _recalculate_proxy(self):
        if isinstance(prx := self._table_proxy(), proxy.SortProxy):
            self.model()._proxy = prx.from_dataframe(
                prx.index, self.model().df, ascending=prx.ascending
            )

    def _map_row_index(self, r: _Index) -> _Index:
        if isinstance(prx := self._table_proxy(), proxy.SortProxy):
            if isinstance(r, slice):
                r1 = prx.map(np.arange(r.start, r.stop))
            else:
                r1 = prx.map(r)
        else:
            r1 = r
        return r1

    if TYPE_CHECKING:

        def model(self) -> QDataFrameModel: ...


@register_function(command_id="builtins:QDataFrameView:select-columns", menus=[])
def select_columns(model: WidgetDataModel) -> Parametric:
    """Select columns, used for dragging columns off a dataframe."""

    def run(columns: list[int]) -> WidgetDataModel:
        df = wrap_dataframe(model.value)
        nrows = df.num_rows()
        dict_out = {}
        for icol in columns:
            dict_out.update(
                df.get_subset(slice(0, nrows), slice(icol, icol + 1)).to_dict()
            )
        df = df.from_dict(dict_out)
        return model.with_value(df.unwrap())

    return run


class QDictView(QDataFrameView):
    """A widget for viewing dictionary with scalar values."""

    __himena_widget_id__ = "builtins:QDictView"
    __himena_display_name__ = "Built-in Dictionary Viewer"

    def __init__(self, ui: MainWindow):
        super().__init__(ui)
        self._extension_default = ".json"
        self._model_type = StandardType.DICT
        self.horizontalHeader().hide()

    @validate_protocol
    def update_model(self, model: WidgetDataModel[dict]):
        if not isinstance(model.value, Mapping):
            raise TypeError(f"Expected a mapping, got {type(model.value)}.")
        was_empty = self.model() is None
        df = wrap_dataframe({k: [v] for k, v in model.value.items()})
        self.setModel(QDataFrameModel(df, transpose=True))
        if was_empty:
            self.resizeColumnsToContents()
        if ext := model.extension_default:
            self._extension_default = ext
        self.control_widget().update_for_table(self)
        self._model_type = model.type
        self.update()

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value={k: v[0] for k, v in self.model().df.to_dict().items()},
            type=self.model_type(),
            extension_default=self._extension_default,
        )

    @validate_protocol
    def size_hint(self):
        return 260, 260


class QDataFrameViewControl(QtW.QWidget):
    """A control widget for QDataFrameView."""

    def __init__(self, table: QDataFrameView):
        super().__init__()
        _R_CENTER = (
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        self._selection_range = QSelectionRangeEdit()

        groupbox_other = QToolButtonGroup(self)
        self._tool_buttons = [
            groupbox_other.add_tool_button(table._auto_resize_columns, "resize_col"),
            groupbox_other.add_tool_button(table._sort_table_by_column, "sort_table"),
        ]

        layout.addWidget(spacer_widget())
        layout.addWidget(self._label)
        layout.addWidget(groupbox_other)
        layout.addWidget(self._selection_range)

    def update_for_table(self, table: QDataFrameView | None):
        if table is None:
            return
        model = table.model()
        self._label.setText(
            f"{model.df.type_name()} ({model.rowCount()}, {model.columnCount()})"
        )
        self._selection_range.connect_table(table)

    def update_theme(self, theme):
        """Update the theme of the control."""
        for btn in self._tool_buttons:
            btn.update_theme(theme)


class QDataFramePlotView(QtW.QSplitter):
    """A widget for viewing a dataframe on the left and its plot on the right.

    ## Basic Usage

    All the columns of the dataframe must be numerical data type. If there's only one
    column, it will be considered as the y values. If there are more, the first column
    will be the x values and the rest of the columns will be separate y values. If there
    are more than one set of y values, clicking the column will highlight the plot on
    the right.
    """

    __himena_widget_id__ = "builtins:QDataFramePlotView"
    __himena_display_name__ = "Built-in DataFrame Plot View"

    def __init__(self, ui: MainWindow):
        from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas

        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self._table_widget = QDataFrameView(ui)
        self._table_widget.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self._plot_widget = QModelMatplotlibCanvas()
        self._plot_widget.update_model(
            WidgetDataModel(value=hplt.figure(), type=StandardType.PLOT)
        )
        right = QtW.QWidget()
        right.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        layout_right = QtW.QVBoxLayout(right)
        layout_right.setContentsMargins(0, 0, 0, 0)
        layout_right.setSpacing(1)
        layout_right.addWidget(self._plot_widget._toolbar)
        layout_right.addWidget(self._plot_widget)
        self._model_type = StandardType.DATAFRAME_PLOT
        self._color_cycle: list[str] | None = None

        self.addWidget(self._table_widget)
        self.addWidget(right)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 2)

        self._table_widget.selection_model.moved.connect(
            self._update_plot_for_selections
        )
        self._y_column_names: list[str] = []

    def createHandle(self):
        return QSplitterHandle(self, side="left")

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        df = wrap_dataframe(model.value)
        col_names = df.column_names()
        if isinstance(meta := model.metadata, DataFramePlotMeta):
            plot_type = meta.plot_type
            plot_background_color = meta.plot_background_color
            plot_color_cycle_name = meta.plot_color_cycle
        else:
            plot_type = "line"
            plot_background_color = "#FFFFFF"
            plot_color_cycle_name = None
        if plot_color_cycle_name is None:
            if np.mean(Color(plot_background_color).rgba) > 0.5:
                plot_color_cycle = Colormap("tab10")
            else:
                plot_color_cycle = Colormap("colorbrewer:Dark2")
        else:
            plot_color_cycle = Colormap(plot_color_cycle_name)

        if len(col_names) == 0:
            raise ValueError("No columns in the dataframe.")
        elif len(col_names) == 1:
            x = np.arange(df.num_rows())
            self._y_column_names = col_names
        else:
            x = df.column_to_array(col_names[0])
            self._y_column_names = col_names[1:]
        fig = hplt.figure(background_color=plot_background_color)
        colors = plot_color_cycle.color_stops.colors
        if colors[0].rgba8[3] == 0:
            colors = colors[1:]
        for i, ylabel in enumerate(self._y_column_names):
            y = df.column_to_array(ylabel)
            color = colors[i % len(colors)]
            if plot_type == "line":
                fig.plot(x, y, color=color, name=ylabel)
            elif plot_type == "scatter":
                fig.scatter(x, y, color=color, name=ylabel)
            else:
                raise ValueError(f"Unsupported plot type: {plot_type!r}")
        self._table_widget.update_model(model)

        # update plot
        model_plot = WidgetDataModel(value=fig, type=StandardType.PLOT)
        self._plot_widget.update_model(model_plot)
        self._model_type = model.type
        self._color_cycle = [c.hex for c in colors]

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        meta = self._table_widget._prep_table_meta()
        return WidgetDataModel(
            value=self._table_widget.model().df.unwrap(),
            type=self.model_type(),
            extension_default=".csv",
            metadata=DataFramePlotMeta(
                current_position=meta.current_position,
                selections=meta.selections,
                plot_type="line",
                plot_color_cycle=self._color_cycle,
                plot_background_color="#FFFFFF",
                rois=_roi.RoiListModel(),
            ),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return self._table_widget.is_modified()

    @validate_protocol
    def is_editable(self) -> bool:
        return self._table_widget.is_editable()

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        self._table_widget.set_editable(value)

    @validate_protocol
    def control_widget(self):
        return self._table_widget.control_widget()

    @validate_protocol
    def size_hint(self):
        return 480, 300

    @validate_protocol
    def widget_added_callback(self):
        # adjuct size
        self.setSizes([160, self.width() - 160])
        self._plot_widget.widget_added_callback()
        return None

    @validate_protocol
    def widget_resized_callback(self, old: Size, new: Size):
        left_width = self._table_widget.width()
        old = old.with_width(max(old.width - left_width, 10))
        new = new.with_width(max(new.width - left_width, 10))
        self._plot_widget.widget_resized_callback(old, new)

    @validate_protocol
    def theme_changed_callback(self, theme):
        # self._table_widget.theme_changed_callback(theme)
        self._plot_widget.theme_changed_callback(theme)

    def _update_plot_for_selections(self, old: Index, new: Index):
        axes_layout = self._plot_widget._plot_models
        if not isinstance(axes_layout, hplt.SingleAxes):
            return
        inds = set()
        for sl in self._table_widget.selection_model.iter_col_selections():
            inds.update(range(sl.start, sl.stop))
        inds.discard(0)  # x axis
        if len(inds) == 0:
            inds = set(range(1, len(self._y_column_names) + 1))

        selected_names = [self._y_column_names[i - 1] for i in inds]

        for model in axes_layout.axes.models:
            selected = model.name in selected_names
            if isinstance(model, hplt.Line):
                model.edge.alpha = 1.0 if selected else 0.4
            elif isinstance(model, hplt.Scatter):
                model.face.alpha = 1.0 if selected else 0.4
                model.edge.alpha = 1.0 if selected else 0.4
        self._plot_widget.update_model(
            WidgetDataModel(value=axes_layout, type=StandardType.PLOT)
        )


@dataclass
class DataFrameConfigs:
    column_drag_enabled: bool = config_field(default=True)
    separator_on_copy: str = config_field(
        default="\\t",
        tooltip="Separator used when the content of table is copied to the clipboard.",
    )


@dataclass
class EditAction:
    old: DataFrameWrapper
    new: DataFrameWrapper
    index: tuple[_Index, _Index]

    def invert(self) -> EditAction:
        return EditAction(self.new, self.old, self.index)

    def apply(self, table: QDataFrameView):
        table.dataframe_update(self.index, self.new, record_undo=False)
