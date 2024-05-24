from __future__ import annotations

from typing import TypeVar
from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from app_model.backends.qt import QModelMainWindow
from royalapp.qt._qtab_widget import QTabWidget
from royalapp.qt._qsub_window import QSubWindow
from royalapp.qt._qdock_widget import QDockWidget

from royalapp.types import DockArea, DockAreaString, TabTitle, WindowTitle
from royalapp.style import get_style
from royalapp.app import get_app

_STYLE_QSS_PATH = Path(__file__).parent / "style.qss"
_T = TypeVar("_T", bound=QtW.QWidget)

class QMainWindow(QModelMainWindow):
    def __init__(self, app: str = "royalapp"):
        _app = get_app("qt")
        _qt_app = _app.get_app()
        
        super().__init__(app)
        self._tab_widget = QTabWidget()
        self._menubar = self.setModelMenuBar({"file": "File"})
        self._toolbar = self.addModelToolBar("toolbar")
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
        self._init_app_model()

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
                DockArea.LEFT, DockArea.RIGHT, DockArea.TOP, DockArea.BOTTOM
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
    
    def add_widget(
        self,
        widget: _T,
        *,
        tab: str | None = None,
        title: str | None = None,
    ) -> QSubWindow[_T]:
        """
        Add a widget to the sub window.

        Parameters
        ----------
        widget : QtW.QWidget
            Widget to add.
        tab : str, optional
            Which tab the widget will be added to. If not given, current tab will be 
            used.
        title : str, optional
            Title of the sub-window. If not given, its name will be automatically 
            generated.

        Returns
        -------
        QSubWindow
            A sub-window widget. The added widget is available by calling 
            `main_widget()` method.
        """
        if tab is None:
            if (sub_window_area := self._tab_widget.currentWidget()) is None:
                sub_window_area = self._tab_widget.addTabArea("Tab")
        else:
            for i in range(self._tab_widget.count()):
                if self._tab_widget.tabText(i) == tab:
                    sub_window_area = self._tab_widget.widget(i)
                    break
            else:
                sub_window_area = self._tab_widget.addTabArea(tab)
        if title is None:
            title = "Window"
        out = sub_window_area.add_sub_window(widget, title)
        self._tab_widget.setCurrentWidget(sub_window_area)
        return out
    
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if widget := self._tab_widget.currentWidget():
            widget._anchor_minimized_windows()
        return None

    def _init_app_model(self):
        from royalapp._app_model import ACTIONS

        self._app.register_actions(ACTIONS)
        self._app.injection_store.register_provider(self._current_tab_name)
        self._app.injection_store.register_provider(self._current_sub_window_title)

    def _current_tab_name(self) -> TabTitle:
        return self._tab_widget.tabText(self._tab_widget.currentIndex())

    def _current_sub_window_title(self) -> WindowTitle:
        if cur := self._tab_widget.currentWidget():
            return cur.activeSubWindow().windowTitle()
        return ""

_DOCK_AREA_MAP = {
    DockArea.TOP: Qt.DockWidgetArea.TopDockWidgetArea,
    DockArea.BOTTOM: Qt.DockWidgetArea.BottomDockWidgetArea,
    DockArea.LEFT: Qt.DockWidgetArea.LeftDockWidgetArea,
    DockArea.RIGHT: Qt.DockWidgetArea.RightDockWidgetArea,
    None: Qt.DockWidgetArea.NoDockWidgetArea,
}
