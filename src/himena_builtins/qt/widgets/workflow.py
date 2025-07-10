from __future__ import annotations

from uuid import UUID
from datetime import timedelta
from functools import singledispatch

from cmap import Color
from qtpy import QtWidgets as QtW, QtGui
from magicgui.widgets import request_values
from himena import workflow as _wf
from himena.consts import StandardType
from himena.plugins import validate_protocol
from himena.qt._utils import get_main_window
from himena.qt._qflowchart import QFlowChartWidget, BaseNodeItem
from himena.widgets import current_instance, MainWindow
from himena.style import Theme
from himena.types import WidgetDataModel
from himena.workflow._graph import _make_mock_main_window


class WorkflowNodeItem(BaseNodeItem):
    def __init__(self, step: _wf.WorkflowStep, main: MainWindow):
        self._item = _step_to_item(step, main)
        _add_common_child(self._item, step)
        self._step = step

    def text(self) -> str:
        return self._item.text(0)

    def color(self) -> Color:
        if self._step.process_output:
            return Color("#A3F020")
        return Color("#A2A3F0")

    def tooltip(self) -> str:
        return self._item.toolTip(0)

    def content(self) -> str:
        texts = []
        for i in range(self._item.childCount()):
            child = self._item.child(i)
            if child.text(0):
                texts.append(child.text(0))
            for j in range(child.childCount()):
                subchild = child.child(j)
                if subchild.text(0):
                    texts.append(f"  {subchild.text(0)}")
        return "\n".join(texts)

    def id(self):
        return self._step.id


class QWorkflowView(QFlowChartWidget):
    def __init__(self):
        super().__init__()
        self.view.item_right_clicked.connect(self._on_right_clicked)
        self._modified = False
        self._editable = True
        self._workflow: _wf.Workflow = _wf.Workflow()

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        wf = model.value
        if not isinstance(wf, _wf.Workflow):
            raise ValueError(f"Expected Workflow, got {type(wf)}")
        self.set_workflow(wf)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._workflow,
            type=self.model_type(),
            extension_default=".workflow.json",
        )

    @validate_protocol
    def model_type(self) -> str:
        if any(isinstance(step, _wf.UserInput) for step in self._workflow.steps):
            return StandardType.WORKFLOW_PARAMETRIC
        return StandardType.WORKFLOW

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 420

    @validate_protocol
    def is_modified(self) -> bool:
        return self._modified

    @validate_protocol
    def set_modified(self, modified: bool) -> None:
        self._modified = modified

    @validate_protocol
    def is_editable(self) -> bool:
        return self._editable

    @validate_protocol
    def set_editable(self, editable: bool) -> None:
        self._editable = editable

    @validate_protocol
    def theme_changed_callback(self, theme: Theme) -> None:
        self.setBackgroundBrush(QtGui.QColor(Color(theme.background).hex))

    def set_workflow(self, workflow: _wf.Workflow) -> None:
        """Set the workflow."""
        self.scene.clear()
        self.view._node_map.clear()
        self._workflow = workflow
        try:
            main = current_instance()
        except StopIteration:
            main = _make_mock_main_window()
        for step in workflow:
            if step.id not in self.view._node_map:
                self._add_step(step, workflow, main)

    def _add_step(self, step: _wf.WorkflowStep, workflow: _wf.Workflow, main) -> None:
        parents: list[UUID] = []
        for _id in step.iter_parents():
            if _id not in self.view._node_map:
                parent_step = workflow.step_for_id(_id)
                self._add_step(parent_step, workflow, main)
            parents.append(_id)
        item = WorkflowNodeItem(step, main)
        self.view.add_child(item, parents=parents)

    def _replace_with_file_reader(self, item: WorkflowNodeItem, how: str) -> None:
        wf_new = self._workflow.replace_with_input(item.id(), how=how)
        self.set_workflow(wf_new)
        self._modified = True

    def _toggle_to_be_added(self, item: WorkflowNodeItem) -> None:
        step = item._step
        step.process_output = not step.process_output
        self.set_workflow(self._workflow)
        self._modified = True

    def _find_window(self, item: WorkflowNodeItem) -> None:
        step = item._step
        main = get_main_window(self)
        for i_tab, tab in main.tabs.enumerate():
            for i_win, win in tab.enumerate():
                if win._identifier == step.id:
                    main.tabs.current_index = i_tab
                    main.tabs[i_tab].current_index = i_win
                    return None
        raise ValueError("No window in the main window matches the workflow step.")

    def _execute_upto(self, item: WorkflowNodeItem) -> None:
        wf = self._workflow
        wf.filter(item.id()).compute(process_output=True)

    def _edit_user_input(self, item: WorkflowNodeItem) -> None:
        wf = self._workflow
        step = item._step
        if not isinstance(step, _wf.UserInput):
            raise ValueError(f"Expected UserInput, got {type(step)}")
        resp = request_values(
            label={"value": step.label, "label": "Label"},
            doc={"value": step.doc, "label": "Docstring"},
            title="Edit User Input",
            parent=self,
        )
        if resp:
            step.label = resp["label"]
            step.doc = resp["doc"]
            self.set_workflow(wf)  # update
            self._modified = True

    def _on_right_clicked(self, item: WorkflowNodeItem) -> None:
        pos = QtGui.QCursor.pos()
        self._make_context_menu(item).exec(pos)

    def _make_context_menu(self, item: WorkflowNodeItem) -> QtW.QMenu:
        menu = QtW.QMenu(self)
        menu.setToolTipsVisible(True)
        step = item._step
        a0 = menu.addAction(
            "Replace with file reader",
            lambda: self._replace_with_file_reader(item, "file"),
        )
        a0.setToolTip("Replace the selected item with a file reader")
        a1 = menu.addAction(
            "Replace with model input",
            lambda: self._replace_with_file_reader(item, "model"),
        )
        a1.setToolTip("Replace the selected item with a model input")
        a2 = menu.addAction("To be added", lambda: self._toggle_to_be_added(item))
        a2.setCheckable(True)
        a2.setChecked(step.process_output)
        a2.setToolTip(
            "Mark the selected item to add the output to the main window after the \n"
            "workflow execution (even if it's an intermediate step)"
        )
        menu.addSeparator()
        a3 = menu.addAction("Execute upto here", lambda: self._execute_upto(item))
        a3.setToolTip("Execute the workflow up to the selected item")
        a4 = menu.addAction("Find window", lambda: self._find_window(item))
        a4.setToolTip("Find the window that corresponds to the selected item")
        a5 = menu.addAction("Edit ...", lambda: self._edit_user_input(item))
        a5.setToolTip("Edit the selected user input item")

        # update enabled state
        a0.setEnabled(self.is_editable())
        a1.setEnabled(self.is_editable())
        a2.setEnabled(self.is_editable())
        a5.setEnabled(self.is_editable())
        if isinstance(step, _wf.UserInput):
            a3.setEnabled(False)
        else:
            a5.setEnabled(False)
        if item.id() == self._workflow.last_id():
            a2.setEnabled(False)
        return menu


@singledispatch
def _step_to_item(step: _wf.WorkflowStep, main: MainWindow) -> QtW.QTreeWidgetItem:
    raise ValueError(f"Unknown workflow node type {type(step)}")


@_step_to_item.register
def _(step: _wf.LocalReaderMethod, main: MainWindow) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem([f"[Local File]\ntype={step.output_model_type!r}"])
    if isinstance(step.path, list):
        for i, path in enumerate(step.path):
            item.addChild(QtW.QTreeWidgetItem([f"({i}) {path.as_posix()}"]))
    else:
        item.addChild(QtW.QTreeWidgetItem([f"{step.path.as_posix()}"]))
    item.addChild(QtW.QTreeWidgetItem([f"plugin = {step.plugin!r}"]))
    item.setToolTip(0, str(step.path))
    return item


@_step_to_item.register
def _(step: _wf.RemoteReaderMethod, main: MainWindow) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem([f"[Remote File]\ntype={step.output_model_type!r}"])
    item.addChild(QtW.QTreeWidgetItem([f"{step.to_str()}"]))
    item.addChild(QtW.QTreeWidgetItem([f"plugin = {step.plugin!r}"]))
    item.setToolTip(0, str(step.path))
    return item


@_step_to_item.register
def _(step: _wf.UserModification, main: MainWindow) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(["[User Modification]"])
    return item


@_step_to_item.register
def _(step: _wf.UserInput, main: MainWindow) -> QtW.QTreeWidgetItem:
    if step.how == "file":
        text = "File Input"
    elif step.how == "model":
        text = "Model Input"
    else:
        text = "User Input"
    item = QtW.QTreeWidgetItem([f"[{text}]"])
    item.addChild(QtW.QTreeWidgetItem([f"label = {step.label!r}"]))
    item.addChild(QtW.QTreeWidgetItem([f"doc = {step.doc!r}"]))
    item.setToolTip(0, f"{text}\nlabel = {step.label}\ndoc = {step.doc}")
    return item


@_step_to_item.register
def _(step: _wf.CommandExecution, main: MainWindow) -> QtW.QTreeWidgetItem:
    if action := main.model_app.registered_actions.get(step.command_id, None):
        title = action.title
    else:
        title = step.command_id
    item = QtW.QTreeWidgetItem([f"[Command]\n{title}"])
    item.setToolTip(0, step.command_id)
    item.addChild(QtW.QTreeWidgetItem([f"command_id = {step.command_id!r}"]))
    for param in step.parameters or []:
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
            short_desc = "<subwindows>" if param.is_window else "<models>"
            child = QtW.QTreeWidgetItem([f"(parameter) {param.name} = {short_desc}"])
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
            QtW.QTreeWidgetItem([f"execution_time = {timedelta(seconds=dt)}"])
        )
    return item


@_step_to_item.register
def _(step: _wf.ProgrammaticMethod, main: MainWindow) -> QtW.QTreeWidgetItem:
    item = QtW.QTreeWidgetItem(
        [f"[Programmatic Method]\ntype={step.output_model_type!r}"]
    )
    return item


def _add_common_child(item: QtW.QTreeWidgetItem, step: _wf.WorkflowStep):
    item.addChild(
        QtW.QTreeWidgetItem([f"datetime = {step.datetime:%Y-%m-%d %H:%M:%S}"])
    )
    return item
