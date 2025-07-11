from __future__ import annotations
from typing import Iterable
import weakref
from qtpy.QtCore import QTimer
from himena.plugins import validate_protocol
from himena.widgets import MainWindow, SubWindow
import himena.workflow as _wf
from himena_builtins.qt.widgets.workflow import QWorkflowViewBase, WorkflowNodeItem


class QFullWorkflowView(QWorkflowViewBase):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui_ref = weakref.ref(ui)
        self.view.item_left_clicked.connect(self._find_window)
        self._single_shot = QTimer.singleShot  # just for testing

    @validate_protocol
    def widget_added_callback(self):
        if ui := self._ui_ref():
            for win in ui.iter_windows():
                self.add_workflow(win._widget_workflow)
            ui.events.window_added.connect(self._window_added)
            ui.events.window_closed.connect(self._window_closed)
            ui.events.window_activated.connect(self._window_activated)

    def _window_added(self, win: SubWindow):
        self._single_shot(0, lambda win=win: self.add_window(win))

    def _window_closed(self, win_closed: SubWindow):
        if ui := self._ui_ref():
            workflows: list[_wf.Workflow] = []
            for win in ui.iter_windows():
                if win is win_closed:
                    continue
                workflows.append(win._widget_workflow)
            self.reset_workflows(workflows)

    def _window_activated(self, win: SubWindow):
        if node := self.view._node_map.get(win._identifier):
            node.setSelected(True)

    def _find_window(self, item: WorkflowNodeItem) -> None:
        if ui := self._ui_ref():
            step = item._step
            for i_tab, tab in ui.tabs.enumerate():
                for i_win, win in tab.enumerate():
                    if win._identifier == step.id:
                        ui.tabs.current_index = i_tab
                        ui.tabs[i_tab].current_index = i_win
                        return None

    def add_window(self, window: SubWindow) -> None:
        """Add a window's workflow to the view."""
        if not window._widget_workflow:
            return
        self.add_workflow(window._widget_workflow)

    def reset_workflows(self, workflows: Iterable[_wf.Workflow]) -> None:
        """Remove the workflow from the view."""
        not_visited = self.view._node_map.copy()
        for workflow in workflows:
            for step in workflow:
                not_visited.pop(step.id, None)
        self.view.remove_nodes(not_visited.values())
