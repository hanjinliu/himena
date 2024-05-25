from __future__ import annotations

from typing import TypeVar
from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from app_model.backends.qt import QModelMainWindow
from royalapp.qt._qtab_widget import QTabWidget
from royalapp.qt._qsub_window import QSubWindow, QSubWindowArea
from royalapp.qt._qdock_widget import QDockWidget
from royalapp import _app_model
from royalapp.types import (
    DockArea,
    DockAreaString,
    NewWidgetBehavior,
    TabTitle,
    WindowTitle,
    FileData,
)
from royalapp.style import get_style
from royalapp.app import get_app
from royalapp.qt._widget_registry import pick_provider

_STYLE_QSS_PATH = Path(__file__).parent / "style.qss"
_T = TypeVar("_T", bound=QtW.QWidget)


class QMainWindow(QModelMainWindow, _app_model.MainWindowMixin):
    def __init__(
        self,
        app: str = "royalapp",
        *,
        new_widget_behavior: NewWidgetBehavior = NewWidgetBehavior.WINDOW,
    ):
        _app = get_app("qt")
        self._qt_app = _app.get_app()
        self._app_name = app

        app_model_app = _app_model.get_application(app)
        super().__init__(app_model_app)
        self._tab_widget = QTabWidget()
        self._menubar = self.setModelMenuBar(menu_ids={"file": "File"})
        self._toolbar = self.addModelToolBar(menu_id="toolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setFixedHeight(32)
        self.setCentralWidget(self._tab_widget)

        style = get_style("default")
        style_text = (
            _STYLE_QSS_PATH.read_text()
            .replace("$(foreground-1)", style.foreground.level_1)
            .replace("$(foreground-2)", style.foreground.level_2)
            .replace("$(foreground-3)", style.foreground.level_3)
            .replace("$(background-1)", style.background.level_1)
            .replace("$(background-2)", style.background.level_2)
            .replace("$(background-3)", style.background.level_3)
        )
        self.setStyleSheet(style_text)
        self._new_widget_behavior = NewWidgetBehavior(new_widget_behavior)
        _app_model.set_current_instance(app, self)

    def add_dock_widget(
        self,
        widget: QtW.QWidget,
        *,
        title: str | None = None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ) -> QDockWidget:
        if title is None:
            title = widget.objectName()
        if allowed_areas is None:
            allowed_areas = [
                DockArea.LEFT,
                DockArea.RIGHT,
                DockArea.TOP,
                DockArea.BOTTOM,
            ]
        else:
            allowed_areas = [DockArea(area) for area in allowed_areas]
        dock_widget = QDockWidget(widget, title)
        areas = Qt.DockWidgetArea.NoDockWidgetArea
        for allowed_area in allowed_areas:
            areas |= _DOCK_AREA_MAP[allowed_area]
        dock_widget.setAllowedAreas(areas)
        self.addDockWidget(_DOCK_AREA_MAP[area], dock_widget)
        return dock_widget

    def add_tab(self, tab_name: str) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        return self._tab_widget.addTabArea(tab_name)

    def add_widget(
        self,
        widget: _T,
        *,
        title: str | None = None,
    ) -> QSubWindow[_T]:
        """
        Add a widget to the sub window.

        Parameters
        ----------
        widget : QtW.QWidget
            Widget to add.
        title : str, optional
            Title of the sub-window. If not given, its name will be automatically
            generated.

        Returns
        -------
        QSubWindow
            A sub-window widget. The added widget is available by calling
            `main_widget()` method.
        """
        if self._new_widget_behavior is NewWidgetBehavior.WINDOW:
            if (sub_window_area := self._tab_widget.currentWidget()) is None:
                sub_window_area = self._tab_widget.addTabArea()
        else:
            sub_window_area = self._tab_widget.addTabArea(title)
        out = sub_window_area.add_widget(widget, title=title)
        self._tab_widget.setCurrentWidget(sub_window_area)
        if self._new_widget_behavior is NewWidgetBehavior.TAB:
            out.state = "full"
        return out

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if widget := self._tab_widget.currentWidget():
            widget._reanchor_windows()
        return None

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if widget := self._tab_widget.currentWidget():
            widget._reanchor_windows()
        return None

    def event(self, e: QtCore.QEvent) -> bool:
        if e.type() in {
            QtCore.QEvent.Type.WindowActivate,
            QtCore.QEvent.Type.ZOrderChange,
        }:
            # upon activation or raise_, put window at the end of _instances
            _app_model.set_current_instance(self._app_name, self)

        res = super().event(e)

        if e.type() == QtCore.QEvent.Type.Close and e.isAccepted():
            _app_model.remove_instance(self._app_name, self)

        return res

    def show(self, run: bool = False) -> None:
        super().show()
        if run:
            get_app("qt").run_app()
        return None

    def _provide_current_tab_name(self) -> TabTitle:
        idx = self._tab_widget.currentIndex()
        return self._tab_widget.tabText(idx)

    def _provide_current_sub_window_title(self) -> WindowTitle:
        raise self._tab_widget.currentWidget().windowTitle()

    def _process_file_input(self, file_data: FileData) -> None:
        widget = pick_provider(file_data)(file_data)
        self._tab_widget.currentWidget().add_widget(widget)

    def _provide_file_output(self) -> FileData:
        if sub := self._tab_widget.currentWidget().currentSubWindow():
            active_window = sub.main_widget()
            if not hasattr(active_window, "as_file_data"):
                raise ValueError("Widget does not have `as_file_data` method.")
            return active_window.as_file_data()
        else:
            raise ValueError("No active window.")

    def _open_file_dialog(self, mode: str = "r") -> Path | list[Path] | None:
        if mode == "r":
            path = QtW.QFileDialog.getOpenFileName(self, "Open File")[0]
            if path:
                return Path(path)
        elif mode == "w":
            path = QtW.QFileDialog.getSaveFileName(self, "Save File")[0]
            if path:
                return Path(path)
        elif mode == "rm":
            paths = QtW.QFileDialog.getOpenFileNames(self, "Open Files")[0]
            if paths:
                return [Path(p) for p in paths]
        elif mode == "d":
            path = QtW.QFileDialog.getExistingDirectory(self, "Open Directory")
            if path:
                return Path(path)
        return None

    def _open_confirmation_dialog(self, message: str) -> bool:
        answer = QtW.QMessageBox.question(self, "Confirmation", message)
        return answer == QtW.QMessageBox.StandardButton.Yes

    def _exit_main_window(self) -> None:
        self.close()

    def _close_current_window(self) -> None:
        self._tab_widget.removeTab(self._tab_widget.currentIndex())
        return None


_DOCK_AREA_MAP = {
    DockArea.TOP: Qt.DockWidgetArea.TopDockWidgetArea,
    DockArea.BOTTOM: Qt.DockWidgetArea.BottomDockWidgetArea,
    DockArea.LEFT: Qt.DockWidgetArea.LeftDockWidgetArea,
    DockArea.RIGHT: Qt.DockWidgetArea.RightDockWidgetArea,
    None: Qt.DockWidgetArea.NoDockWidgetArea,
}
