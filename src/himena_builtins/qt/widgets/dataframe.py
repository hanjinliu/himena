from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, Any, Mapping
import weakref

from cmap import Color, Colormap
import numpy as np
from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from himena import MainWindow
from himena.consts import StandardType
from himena.types import Size, WidgetDataModel, Parametric
from himena.standards import plotting as hplt, roi as _roi
from himena.standards.model_meta import DataFrameMeta, TableMeta, DataFramePlotMeta
from himena.utils.collections import UndoRedoStack
from himena.plugins import validate_protocol, register_function, config_field
from himena.qt import drag_command
from himena.data_wrappers import wrap_dataframe, DataFrameWrapper
from himena_builtins.qt.widgets._table_components import (
    QTableBase,
    QSelectionRangeEdit,
    format_table_value,
    QHorizontalHeaderView,
    Editability,
    FLAGS,
    parse_string,
)
from himena_builtins.qt.widgets._splitter import QSplitterHandle
from himena_builtins.qt.widgets._dragarea import QDraggableArea

if TYPE_CHECKING:
    from himena_builtins.qt.widgets._table_components._selection_model import Index


class QDataFrameModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, df: DataFrameWrapper, transpose: bool = False, parent=None):
        super().__init__(parent)
        self._df = df
        self._transpose = transpose
        self._cfg = DataFrameConfigs()

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
                value = df[r, c]
                dtype = df.get_dtype(c)
                if role == Qt.ItemDataRole.DisplayRole:
                    text = format_table_value(value, dtype.kind)
                else:
                    text = str(value)
                return text
        return QtCore.QVariant()

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


class QDraggableHorizontalHeader(QHorizontalHeaderView):
    """Header view for DataFrameView that supports drag and drop."""

    def __init__(self, parent: QDataFrameView):
        super().__init__(parent)
        self._table_view_ref = weakref.ref(parent)
        self.setMouseTracking(True)
        self._hover_drag_indicator = QDraggableArea(self)
        self._hover_drag_indicator.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
        )
        self._hover_drag_indicator.setFixedSize(14, 14)
        self._hover_drag_indicator.hide()
        self._hover_drag_indicator.dragged.connect(self._drag_event)
        self._drag_enabled = True

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        view = self._table_view_ref()
        if view is None or not self._drag_enabled:
            return super().mouseMoveEvent(e)
        if e.button() == QtCore.Qt.MouseButton.NoButton:
            # hover
            index = self.logicalIndexAt(e.pos())
            self._process_move_event(index)
        return super().mouseMoveEvent(e)

    def _process_move_event(self, index: int):
        view = self._table_view_ref()
        hovered_column_selected = False
        for sel in view.selection_model.iter_col_selections():
            if sel.start <= index < sel.stop:
                hovered_column_selected = True
                break
        if hovered_column_selected and index >= 0:
            index_rect = self.visualRectAtIndex(index)
            top_right = index_rect.topRight()
            top_right.setX(top_right.x() - 14)
            dy = (index_rect.height() - self._hover_drag_indicator.height()) / 2
            top_right.setY(top_right.y() + int(dy))
            self._hover_drag_indicator.move(top_right)
            self._hover_drag_indicator.show()
        else:
            self._hover_drag_indicator.hide()

    def leaveEvent(self, a0):
        self._hover_drag_indicator.hide()
        return super().leaveEvent(a0)

    def _data_model_for_drag(self) -> QtGui.QDrag | None:
        view = self._table_view_ref()
        if view is None or not self._drag_enabled:
            return
        cols = [sel.start for sel in view.selection_model.iter_col_selections()]
        model = view.to_model()
        df = wrap_dataframe(model.value)
        s = "" if len(cols) == 1 else "s"
        return drag_command(
            view,
            "builtins:QDataFrameView:select-columns",
            StandardType.DATAFRAME,
            with_params={"columns": cols},
            desc=f"{df.num_columns()} column{s}",
            text_data=lambda: df.to_csv_string("\t"),
            exec=False,
        )

    def _drag_event(self):
        if drag := self._data_model_for_drag():
            drag.exec()


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

    def __init__(self, ui):
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
    def control_widget(self):
        if self._control is None:
            self._control = QDataFrameViewControl()
        return self._control

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        _ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        _shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if _ctrl and e.key() == QtCore.Qt.Key.Key_C:
            return self.copy_data(header=_shift)
        elif _ctrl and e.key() == QtCore.Qt.Key.Key_V:
            if clipboard := QtGui.QGuiApplication.clipboard():
                return self.paste_data(clipboard.text())
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

    def edit_item(self, r: int, c: int, value: str):
        self.model().setData(self.model().index(r, c), value, Qt.ItemDataRole.EditRole)
        # datChanged needs to be emitted manually
        self.model().dataChanged.emit(
            self.model().index(r, c),
            self.model().index(r, c),
            [Qt.ItemDataRole.EditRole],
        )

    def copy_data(self, header: bool = False):
        rng = self._selection_model.get_single_range()

        rsl, csl = rng
        r0, r1 = rsl.start, rsl.stop
        c0, c1 = csl.start, csl.stop
        csv_text = (
            self.model()
            .df.get_subset(r0, r1, c0, c1)
            .to_csv_string("\t", header=header)
        )
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(csv_text)

    def paste_data(self, text: str):
        """Paste a text data to the selected cells."""
        if not text:
            return
        buf = StringIO(text)
        arr_paste = np.loadtxt(
            buf, dtype=np.dtypes.StringDType(), delimiter="\t", ndmin=2
        )
        rsl, csl = self._selection_model.current_range
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

        self.dataframe_update((r0, c0), wrap_dataframe(df_paste))
        self.update()

    def dataframe_update(
        self,
        top_left: tuple[int, int],
        df: DataFrameWrapper,
        record_undo: bool = True,
    ):
        r0, c0 = top_left
        r1, c1 = r0 + df.num_rows(), c0 + df.num_columns()
        _model = self.model()
        old = _model.df.get_subset(r0, r1, c0, c1).copy()
        if r1 > _model.df.num_rows() or c1 > _model.df.num_columns():
            raise ValueError("Pasting values exceed the table dimensions.")

        column_names = _model.df.column_names()
        _df_updated = _model.df
        for i_col in range(c0, c1):
            name = column_names[i_col]
            target = _model.df.column_to_array(name).copy()
            target[r0:r1] = df.column_to_array(name)
            _df_updated = _df_updated.with_columns({name: target})
        new = _df_updated.get_subset(r0, r1, c0, c1).copy()
        _model._df = _df_updated
        if record_undo:
            self._undo_stack.push(EditAction(old, new, (r0, c0)))

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Copy", self.copy_data)
        menu.addAction("Copy With Header", lambda: self.copy_data(header=True))
        return menu

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
            dict_out.update(df.get_subset(0, nrows, icol, icol + 1).to_dict())
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
        return None

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
    def __init__(self):
        super().__init__()
        _R_CENTER = (
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        layout.addWidget(self._label)
        self._selection_range = QSelectionRangeEdit()
        layout.addWidget(self._selection_range)

    def update_for_table(self, table: QDataFrameView | None):
        if table is None:
            return
        model = table.model()
        self._label.setText(
            f"{model.df.type_name()} ({model.rowCount()}, {model.columnCount()})"
        )
        self._selection_range.connect_table(table)


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
        return None

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
        return None


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
    index: tuple[int, int]

    def invert(self) -> EditAction:
        return EditAction(self.new, self.old, self.index)

    def apply(self, table: QDataFrameView):
        table.dataframe_update(self.index, self.new, record_undo=False)
