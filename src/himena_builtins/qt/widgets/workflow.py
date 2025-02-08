from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from functools import singledispatch
from datetime import timedelta
from himena.consts import StandardType, MonospaceFontFamily
from himena.plugins import validate_protocol
from himena import workflow as _wf
from himena.qt._utils import drag_model
from himena_builtins.qt.widgets._table_components._selection_model import (
    SelectionModel,
    Index,
)
from himena.types import WidgetDataModel


class QWorkflowView(QtW.QWidget):
    """A widget that displays a workflow of another widget.

    A workflow is a directed acyclic graph of operations. Each operation is represented
    by a item in this widget. The item can be expanded to show the details. The parents
    of the selected item are highlighted with dashed lines.
    """

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tree_widget = QWorkflowTree(_wf.Workflow())
        self._tree_widget.setColumnCount(1)
        self._tree_widget.setHeaderHidden(True)
        layout.addWidget(self._tree_widget)
        self._tree_widget.setFont(QtGui.QFont(MonospaceFontFamily))

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        wf = model.value
        if not isinstance(wf, _wf.Workflow):
            raise ValueError(f"Expected Workflow, got {type(wf)}")
        self._tree_widget.set_workflow(wf)
        for each in wf:
            item = _step_to_item(each)
            _add_common_child(item, each)
            self._tree_widget.addTopLevelItem(item)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._tree_widget._workflow,
            type=self.model_type(),
            extension_default=".workflow.json",
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.WORKFLOW

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 320


class QWorkflowTree(QtW.QTreeWidget):
    def __init__(self, workflow: _wf.Workflow):
        super().__init__()
        self._workflow = workflow
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self._current_index = 0
        self._selection_color = QtGui.QColor("#777777")
        self._hover_color = QtGui.QColor(self._selection_color)
        self._selection_model = SelectionModel(
            row_count=lambda: len(self._workflow), col_count=lambda: 1
        )
        self._selection_model.moved.connect(self._on_moved)
        self._id_to_index_map = {}

    def set_workflow(self, workflow: _wf.Workflow):
        self.clear()
        self._workflow = workflow
        self._id_to_index_map = workflow.id_to_index_map()

    @QtCore.Property(QtGui.QColor)
    def selectionColor(self):
        return self._selection_color

    @selectionColor.setter
    def selectionColor(self, color: QtGui.QColor):
        self._selection_color = color
        self._hover_color = QtGui.QColor(color)
        self._hover_color.setAlpha(128)

    def keyPressEvent(self, event):
        _key = event.key()
        _mod = event.modifiers()
        if _key == QtCore.Qt.Key.Key_Up:
            if _mod & QtCore.Qt.KeyboardModifier.ControlModifier:
                dr = -99999999
            else:
                dr = -1
            self._selection_model.move(dr, 0)
            return
        elif _key == QtCore.Qt.Key.Key_Down:
            if _mod & QtCore.Qt.KeyboardModifier.ControlModifier:
                dr = 99999999
            else:
                dr = 1
            self._selection_model.move(dr, 0)
            return
        return super().keyPressEvent(event)

    def _on_moved(self, src: Index, dst: Index) -> None:
        """Update the view."""
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Paint table and the selection."""
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())

        idx = self._selection_model.current_index
        item = self.itemFromIndex(self.model().index(idx.row, 0))
        if item is None:
            return None
        rect = self._rect_for_row(idx.row)
        pen = QtGui.QPen(self._selection_color, 2)
        painter.setPen(pen)
        painter.drawRect(rect)

        # draw parents
        pen.setWidth(1)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for step in self._workflow[idx.row].iter_parents():
            try:
                index = self._id_to_index_map[step]
            except KeyError:  # This should not happen but just in case
                continue
            rect = self._rect_for_row(index)
            painter.drawRect(rect)

        return None

    def _rect_for_row(self, row: int) -> QtCore.QRect:
        index = self.model().index(row, 0)
        item = self.ancestor_item(index)
        if item is None:
            return QtCore.QRect()
        if item.isExpanded():
            rect = self.visualRect(index)
            child = item.child(item.childCount() - 1)
            if child is not None:
                index = self.indexFromItem(child)
                rect = rect.united(self.visualRect(index))
        else:
            rect = self.visualRect(index)
        return rect.adjusted(1, 1, -1, -1)

    def ancestor_item(self, index: QtCore.QModelIndex) -> QtW.QTreeWidgetItem | None:
        item = self.itemFromIndex(index)
        if item is None:
            return None
        while parent := item.parent():
            item = parent
        return item

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        index = self.indexAt(e.pos())
        item = self.ancestor_item(index)
        if item is not None:
            row = self.indexOfTopLevelItem(item)
            self._selection_model.jump_to(row, 0)
        return super().mousePressEvent(e)

    # drag-and-drop
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._start_drag(e.pos())
            return None
        return super().mouseMoveEvent(e)

    def _start_drag(self, pos: QtCore.QPoint):
        if not self.indexAt(pos).isValid():
            return
        row = self._selection_model.current_index.row
        if 0 <= row < len(self._workflow):
            wf_filt = self._workflow.filter(self._workflow[row].id)
            drag_model(
                WidgetDataModel(
                    value=wf_filt,
                    type=StandardType.WORKFLOW,
                    title="Subset of workflow",
                ),
                desc="workflow node",
                source=self.parent(),
                text_data=str(wf_filt),
            )


_STEP_ROLE = QtCore.Qt.ItemDataRole.UserRole


@singledispatch
def _step_to_item(step: _wf.WorkflowStep) -> QtW.QTreeWidgetItem:
    raise ValueError(f"Unknown workflow node type {type(step)}")


@_step_to_item.register
def _(step: _wf.LocalReaderMethod) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem([f"[Local Path] (type={step.output_model_type!r})"])
    if isinstance(step.path, list):
        for i, path in enumerate(step.path):
            item.addChild(QtW.QTreeWidgetItem([f"({i}) {path.as_posix()}"]))
    else:
        item.addChild(QtW.QTreeWidgetItem([f"{step.path.as_posix()}"]))
    item.addChild(QtW.QTreeWidgetItem([f"plugin = {step.plugin!r}"]))
    item.setToolTip(0, str(step.path))
    item.setData(0, _STEP_ROLE, step)
    return item


@_step_to_item.register
def _(step: _wf.SCPReaderMethod) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem([f"[Remote Path] (type={step.output_model_type!r})"])
    item.addChild(QtW.QTreeWidgetItem([f"{step.to_str()}"]))
    item.addChild(QtW.QTreeWidgetItem([f"plugin = {step.plugin!r}"]))
    item.setToolTip(0, str(step.path))
    item.setData(0, _STEP_ROLE, step)
    return item


@_step_to_item.register
def _(step: _wf.UserModification) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(["[User Modification]"])
    item.setData(0, _STEP_ROLE, step)
    return item


@_step_to_item.register
def _(step: _wf.CommandExecution) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem([f"[Command] {step.command_id}"])
    item.setToolTip(0, step.command_id)
    for param in step.parameters:
        if isinstance(param, _wf.UserParameter):
            child = QtW.QTreeWidgetItem([f"(parameter) {param.name} = {param.value!r}"])
        elif isinstance(param, _wf.ModelParameter):
            child = QtW.QTreeWidgetItem(
                [f"(parameter) {param.name} = <data model, type={param.model_type!r}>"]
            )
        elif isinstance(param, _wf.WindowParameter):
            child = QtW.QTreeWidgetItem(
                [f"(parameter) {param.name} = <window, type={param.model_type!r}>"]
            )
        elif isinstance(param, _wf.ListOfModelParameter):
            child = QtW.QTreeWidgetItem([f"(parameter) {param.name} = <models>"])
        else:
            raise ValueError(f"Unknown parameter type {type(param)}")
        item.addChild(child)
    for ctx in step.contexts:
        if isinstance(ctx, _wf.ModelParameter):
            child = QtW.QTreeWidgetItem(
                [f"(context) <data model, type={ctx.model_type!r}>"]
            )
        elif isinstance(ctx, _wf.WindowParameter):
            child = QtW.QTreeWidgetItem(
                [f"(context) <window, type={ctx.model_type!r}>"]
            )
        else:
            raise ValueError(f"Unknown context type {type(ctx)}")
        item.addChild(child)
    if (dt := step.execution_time) > 0.0:
        item.addChild(
            QtW.QTreeWidgetItem([f"execution time = {timedelta(seconds=dt)}"])
        )
    item.setData(0, _STEP_ROLE, step)
    return item


@_step_to_item.register
def _(step: _wf.ProgrammaticMethod) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(
        [f"[Programmatic Method] (type={step.output_model_type!r})"]
    )
    item.setData(0, _STEP_ROLE, step)
    return item


def _add_common_child(item: QtW.QTreeWidgetItem, step: _wf.WorkflowStep):
    item.addChild(
        QtW.QTreeWidgetItem([f"datetime = {step.datetime:%Y-%m-%d %H:%M:%S}"])
    )
    return item
