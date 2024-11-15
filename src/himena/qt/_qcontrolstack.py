from __future__ import annotations

from qtpy import QtWidgets as QtW


class QControlStack(QtW.QStackedWidget):
    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        # window content -> control widget
        self._empty_widget = QtW.QWidget()
        self._widget_map: dict[QtW.QWidget, QtW.QWidget] = {}
        self.addWidget(self._empty_widget)

    def add_control_widget(
        self,
        widget: QtW.QWidget,
        control: QtW.QWidget,
    ) -> None:
        self.addWidget(control)
        self._widget_map[widget] = control
        self.setCurrentWidget(control)

    def remove_control_widget(self, widget: QtW.QWidget) -> None:
        if control := self._widget_map.pop(widget, None):
            self.removeWidget(control)

    def update_control_widget(self, current: QtW.QWidget | None) -> None:
        if control := self._widget_map.get(current):
            self.setCurrentWidget(control)
        else:
            self.setCurrentWidget(self._empty_widget)
