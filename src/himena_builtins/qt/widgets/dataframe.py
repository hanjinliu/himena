from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
import weakref

from cmap import Color, Colormap
import numpy as np
from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.types import Size, WidgetDataModel, Parametric
from himena.standards import plotting as hplt, roi as _roi
from himena.standards.model_meta import DataFrameMeta, TableMeta, DataFramePlotMeta
from himena.utils.collections import UndoRedoStack
from himena.plugins import validate_protocol, register_function
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
        # this set records all the updated column indices for copy-on-write behavior
        self._updated_columns: set[int] = set()

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
            i_row, i_col = index.row(), index.column()
            val = parse_string(value, self.df.get_dtype(i_col).kind)
            name = self.df.column_names()[i_col]
            col = self.df.column_to_array(name)
            if i_col not in self._updated_columns:
                col = col.copy()
                self._updated_columns.add(i_col)
            col[i_row] = val
            self._df = self.df.with_columns({name: col})
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

    def __init__(self):
        super().__init__()
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
        self.setModel(QDataFrameModel(df, transpose=transpose))
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

        if self._control is None:
            self._control = QDataFrameViewControl()
        self._control.update_for_table(self)
        self._model_type = model.type
        self.update()
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        # NOTE: if this model is passed to another widget and modified in this widget,
        # the other dataframe will be modified as well. To avoid this, we need to reset
        # the copy-on-write state of this array.
        self.model()._updated_columns.clear()
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
        return self._control

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.matches(QtGui.QKeySequence.StandardKey.Copy):
            return self.copy_data()
        if (
            e.modifiers() & Qt.KeyboardModifier.ControlModifier
            and e.key() == QtCore.Qt.Key.Key_F
        ):
            self._find_string()
            return
        return super().keyPressEvent(e)

    def copy_data(self):
        rng = self._selection_model.get_single_range()

        rsl, csl = rng
        r0, r1 = rsl.start, rsl.stop
        c0, c1 = csl.start, csl.stop
        csv_text = self.model().df.get_subset(r0, r1, c0, c1).to_csv_string("\t")
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(csv_text)

    def edit_item(self, r: int, c: int, value: str):
        self.model().setData(self.model().index(r, c), value, Qt.ItemDataRole.EditRole)
        # datChanged needs to be emitted manually
        self.model().dataChanged.emit(
            self.model().index(r, c),
            self.model().index(r, c),
            [Qt.ItemDataRole.EditRole],
        )

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Copy", self.copy_data)
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
        return None


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

    def __init__(self):
        from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas

        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self._table_widget = QDataFrameView()
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
    column_drag_enabled: bool = field(default=True)
    separator_on_copy: str = field(
        default="\\t",
        metadata={
            "tooltip": "Separator used when the content of table is copied to the clipboard."
        },
    )


@dataclass
class EditAction:
    old: Any
    new: Any
    index: Any

    def invert(self) -> EditAction:
        return EditAction(self.new, self.old, self.index)

    def apply(self, table: QDataFrameView):
        raise NotImplementedError
