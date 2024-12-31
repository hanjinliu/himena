from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.consts import StandardType, MonospaceFontFamily
from himena.plugins import validate_protocol
from himena import _descriptors as _d
from himena.qt._utils import drag_model
from himena.types import WidgetDataModel
from himena.widgets import current_instance


class QWorkflowView(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._workflow_node: _d.WorkflowNode | None = None
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tree_widget = QWorkflowTree()
        self._tree_widget.setColumnCount(1)
        self._tree_widget.setHeaderHidden(True)
        layout.addWidget(self._tree_widget)
        self._tree_widget.setFont(QtGui.QFont(MonospaceFontFamily))
        self._control = QWorkflowControl(self)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        wf = model.value
        if not isinstance(wf, _d.WorkflowNode):
            raise ValueError(f"Expected WorkflowNode, got {type(wf)}")
        self._workflow_node = wf
        item = _item_workflow_node(wf)
        self._tree_widget.addTopLevelItem(item)
        self._tree_widget.expandAll()

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._workflow_node,
            type=self.model_type(),
        )

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.WORKFLOW

    @validate_protocol
    def control_widget(self) -> QtW.QWidget:
        return self._control

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 320


class QWorkflowTree(QtW.QTreeWidget):
    def drawBranches(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
        index: QtCore.QModelIndex,
    ):
        # Custom drawing of tree branches
        item = self.itemFromIndex(index)
        if item is None:
            return
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor("gray"), 2))
        font = self.font()
        font.setPixelSize(20)
        painter.setFont(font)
        if item.childCount() > 0:
            if item.isExpanded():
                painter.drawText(rect.bottomLeft(), "-")
            else:
                painter.drawText(rect.bottomLeft(), "+")
        xright = rect.right()
        xleft = xright - rect.height() // 2 + 1
        ytop = rect.top() + 2
        ymid = rect.center().y()
        painter.drawLine(xleft, ytop, xleft, ymid)
        painter.drawLine(xleft, ymid, xright, ymid)
        painter.restore()

    # drag-and-drop
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._start_drag(e.pos())
            return None
        return super().mouseMoveEvent(e)

    def _start_drag(self, pos: QtCore.QPoint):
        item = self.itemAt(pos)
        if item is not None:
            item.setSelected(False)
            wf = item.data(0, WORKFLOW_ROLE)
            if not isinstance(wf, _d.WorkflowNode):
                return
            drag_model(
                WidgetDataModel(
                    value=wf,
                    type=StandardType.WORKFLOW,
                    title="Subset of workflow",
                ),
                desc="workflow node",
                source=self.parent(),
                text_data=wf.render_history(),
            )


class QWorkflowControl(QtW.QWidget):
    def __init__(self, view: QWorkflowView):
        super().__init__()
        self._view = view
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._run_button = QtW.QPushButton("Run")
        layout.addWidget(QtW.QWidget(), stretch=10)
        layout.addWidget(self._run_button)
        self._run_button.clicked.connect(self._run_workflow)

    def _run_workflow(self):
        if self._view._workflow_node is None:
            return
        self._view._workflow_node.get_model(current_instance())


WORKFLOW_ROLE = QtCore.Qt.ItemDataRole.UserRole


def _item_workflow_node(wf: _d.WorkflowNode) -> QtW.QTreeWidgetItem:
    if isinstance(wf, _d.CommandExecution):
        return _item_command_execution(wf)
    elif isinstance(wf, _d.LocalReaderMethod):
        return _item_local_reader(wf)
    elif isinstance(wf, _d.SCPReaderMethod):
        return _item_scp_reader(wf)
    elif isinstance(wf, _d.UserModification):
        return _item_user_modification(wf)
    elif isinstance(wf, _d.ProgramaticMethod):
        return _item_programatic(wf)
    raise ValueError(f"Unknown workflow node type {type(wf)}")


def _item_local_reader(wf: _d.LocalReaderMethod) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(["[Local Path]"])
    if isinstance(wf.path, list):
        for path in wf.path:
            item.addChild(QtW.QTreeWidgetItem([f"[Path] {path.as_posix()}"]))
    else:
        item.addChild(QtW.QTreeWidgetItem([f"[Path] {wf.path.as_posix()}"]))
    item.addChild(QtW.QTreeWidgetItem([f"[Plugin] {wf.plugin}"]))
    item.setData(0, WORKFLOW_ROLE, wf)
    item.setToolTip(0, str(wf.path))
    return item


def _item_scp_reader(wf: _d.SCPReaderMethod) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(["[Remote Path]"])
    item.addChild(QtW.QTreeWidgetItem([wf._file_path_repr()]))
    item.addChild(QtW.QTreeWidgetItem([f"[Plugin] {wf.plugin}"]))
    item.setData(0, WORKFLOW_ROLE, wf)
    item.setToolTip(0, str(wf.path))
    return item


def _item_user_modification(wf: _d.UserModification) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(["[User Modification]"])
    item.setData(0, WORKFLOW_ROLE, wf)
    item.addChild(_item_workflow_node(wf.original))


def _item_command_execution(wf: _d.CommandExecution) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem([f"[Command] {wf.command_id}"])
    item.setData(0, WORKFLOW_ROLE, wf)
    item.setToolTip(0, wf.command_id)
    for param in wf.parameters:
        if isinstance(param, _d.UserParameter):
            child = QtW.QTreeWidgetItem([f"[Parameter] {param.name} = {param.value!r}"])
        elif isinstance(param, (_d.ModelParameter, _d.WindowParameter)):
            child = QtW.QTreeWidgetItem([f"[Parameter] {param.name} ="])
            child.addChild(_item_workflow_node(param.value))
        elif isinstance(param, _d.ListOfModelParameter):
            child = QtW.QTreeWidgetItem([f"[Parameter] {param.name} ="])
            for val in param.value:
                child.addChild(_item_workflow_node(val))
        else:
            raise ValueError(f"Unknown parameter type {type(param)}")
        item.addChild(child)
    for ctx in wf.contexts:
        if isinstance(ctx, (_d.ModelParameter, _d.WindowParameter)):
            item.addChild(_item_workflow_node(ctx.value))
        elif isinstance(ctx, _d.ListOfModelParameter):
            for val in ctx.value:
                item.addChild(_item_workflow_node(val))
        else:
            raise ValueError(f"Unknown context type {type(ctx)}")
    return item


def _item_programatic(wf: _d.ProgramaticMethod) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(["[Programatic Method]"])
    item.setData(0, WORKFLOW_ROLE, wf)
    return item
