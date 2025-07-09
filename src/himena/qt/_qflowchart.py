from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress
from enum import IntEnum
import math
from typing import Hashable
import weakref
import numpy as np
from psygnal import Signal
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, QPointF
from cmap import Color
from himena.consts import MonospaceFontFamily


class BaseNodeItem(ABC):
    @abstractmethod
    def text(self) -> str:
        """Return the text of the node"""

    @abstractmethod
    def color(self) -> Color:
        """Return the color of the node"""

    @abstractmethod
    def tooltip(self) -> str:
        """Return the tooltip text for the node"""

    @abstractmethod
    def id(self) -> Hashable:
        """Return a unique identifier for the node"""

    def content(self) -> str:
        """Return the content of the node, default is the text"""
        return self.text()


class NodeItem(BaseNodeItem):
    def __init__(self, text: str, color: Color | None = None, tooltip: str = ""):
        self._text = text
        self._color = color if color is not None else Color((173, 216, 230))
        self._tooltip = tooltip
        self._id = id(self)

    def text(self) -> str:
        return self._text

    def color(self) -> Color:
        return self._color

    def tooltip(self) -> str:
        return self._tooltip

    def id(self) -> Hashable:
        return self._id


class ZOrder(IntEnum):
    UNDERLAY = -100
    OVERLAY = 100


class QFlowChartNode(QtW.QGraphicsRectItem):
    left_clicked = Signal(object)
    right_clicked = Signal(object)

    def __init__(self, item: BaseNodeItem, x: float = 0.0, y: float = 0.0):
        super().__init__(0, 0, 1, 1)
        self._item = item  # Store the item associated with this node
        self._connected_arrows: list[
            QFlowChartArrow
        ] = []  # List of arrows connected to this node
        self._last_press_pos = QtCore.QPointF()

        # Add text and adjust size
        self.text_item = QtW.QGraphicsTextItem(item.text(), self)
        text_rect = self.text_item.boundingRect()
        width = max(32, text_rect.width() + 8)
        height = max(20, text_rect.height() + 8)
        left = x - width / 2
        top = y - height / 2
        self.setRect(left, top, width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # Set cursor to hand pointer
        self._update_text_position()
        font = QtGui.QFont("Arial", 9)
        self.text_item.setFont(font)

        # Make it movable and selectable
        self.setFlag(QtW.QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtW.QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(
            QtW.QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )

        # Set appearance and other properties
        self.set_text(item.text())
        self.setToolTip(item.tooltip())
        qcolor = QtGui.QColor.fromRgbF(*item.color().rgba)
        self.set_color(qcolor)
        self.setZValue(0)

    def item(self) -> BaseNodeItem:
        """Return the item associated with this node"""
        return self._item

    def _update_text_position(self):
        """Center the text within the node"""
        rect = self.rect()
        center = rect.center()
        text_rect = self.text_item.boundingRect()
        x = center.x() - text_rect.width() / 2
        y = center.y() - text_rect.height() / 2
        self.text_item.setPos(x, y)

    def add_arrow(self, arrow):
        """Add an arrow to the list of connected arrows"""
        if arrow not in self._connected_arrows:
            self._connected_arrows.append(arrow)

    def remove_arrow(self, arrow):
        """Remove an arrow from the list of connected arrows"""
        if arrow in self._connected_arrows:
            self._connected_arrows.remove(arrow)

    def center(self):
        """Get the center point of the node"""
        return self.mapToScene(self.rect().center())

    def _get_edge_point(self, target_point: QPointF) -> QPointF:
        """Get the point on the edge of the node closest to the target point"""
        size = self.rect().size()
        center = self.center()

        # Calculate the intersection point with the rectangle edge
        dx = target_point.x() - center.x()
        dy = target_point.y() - center.y()

        if dx == 0 and dy == 0:
            return center

        # Calculate intersection with rectangle edges
        if abs(dx) / size.width() > abs(dy) / size.height():
            # Intersect with left or right edge
            if dx > 0:
                # Right edge
                edge_x = center.x() + size.width() / 2
                edge_y = center.y() + dy * (size.width() / 2) / abs(dx)
            else:
                # Left edge
                edge_x = center.x() - size.width() / 2
                edge_y = center.y() + dy * (size.width() / 2) / abs(dx)
        else:
            # Intersect with top or bottom edge
            if dy > 0:
                # Bottom edge
                edge_y = center.y() + size.height() / 2
                edge_x = center.x() + dx * (size.height() / 2) / abs(dy)
            else:
                # Top edge
                edge_y = center.y() - size.height() / 2
                edge_x = center.x() + dx * (size.height() / 2) / abs(dy)

        return QPointF(edge_x, edge_y)

    def itemChange(self, change, value):
        """Handle item changes, particularly position changes"""
        if change == QtW.QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update all connected arrows when the node moves
            for arrow in self._connected_arrows:
                arrow._update_position()
            self._update_text_position()
        return super().itemChange(change, value)

    def set_text(self, text):
        """Update the node text"""
        self.text_item.setPlainText(text)
        self._update_text_position()

    def set_color(self, color):
        """Update the node color"""
        brush = QtGui.QBrush(color)
        self.setBrush(brush)
        if brush.color().lightness() < 128:
            self.text_item.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        else:
            self.text_item.setDefaultTextColor(QtGui.QColor(0, 0, 0))

    def mousePressEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        """Handle mouse press events"""
        self._last_press_pos = self.mapFromScene(event.pos())
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        """Handle mouse release events"""
        if (
            self._last_press_pos - self.mapFromScene(event.pos())
        ).manhattanLength() < 4:
            if event.button() == Qt.MouseButton.LeftButton:
                self.left_clicked.emit(self._item)
            elif event.button() == Qt.MouseButton.RightButton:
                self.right_clicked.emit(self._item)
        self._last_press_pos = QtCore.QPointF()
        return super().mouseReleaseEvent(event)


class QFlowChartArrow(QtW.QGraphicsLineItem):
    def __init__(
        self,
        start_node: QFlowChartNode,
        end_node: QFlowChartNode,
        color: QtGui.QColor = Qt.GlobalColor.black,
    ):
        super().__init__()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.start_node = start_node
        self.end_node = end_node
        self.arrowhead_size = 10
        pen = QtGui.QPen(color, 1.2)

        # Set line properties
        self.setPen(pen)

        # Create arrowhead as a separate graphics item
        # Arrowhead as a triangle polygon
        self.arrowhead = QtW.QGraphicsPolygonItem(self)
        pen.setJoinStyle(Qt.PenJoinStyle.SvgMiterJoin)
        self.arrowhead.setBrush(QtGui.QBrush(color))
        self.arrowhead.setPen(pen)

        # Register this arrow with both nodes
        self.start_node.add_arrow(self)
        self.end_node.add_arrow(self)

        # Initial position update
        self._update_position()

    def _update_position(self):
        """Update the arrow position based on the connected nodes"""
        # Get the edge points of both nodes
        start_center = self.start_node.center()
        end_center = self.end_node.center()

        start_point = self.start_node._get_edge_point(end_center)
        end_point = self.end_node._get_edge_point(start_center)

        # Update the main line
        self.setLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())

        # Update arrowhead
        self._update_arrowhead(start_point, end_point)

    def _update_arrowhead(self, start_point: QtCore.QPointF, end_point: QtCore.QPointF):
        """Update the arrowhead position and orientation"""
        # Calculate the angle of the line
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()

        if dx == 0 and dy == 0:
            return

        angle = math.atan2(dy, dx)

        # Calculate arrowhead points
        arrowhead_angle = math.pi / 10  # 18 degrees

        x1 = end_point.x() - self.arrowhead_size * math.cos(angle - arrowhead_angle)
        y1 = end_point.y() - self.arrowhead_size * math.sin(angle - arrowhead_angle)

        x2 = end_point.x() - self.arrowhead_size * math.cos(angle + arrowhead_angle)
        y2 = end_point.y() - self.arrowhead_size * math.sin(angle + arrowhead_angle)

        # Update arrowhead
        self.arrowhead.setPolygon(
            QtGui.QPolygonF(
                [
                    QPointF(end_point.x(), end_point.y()),
                    QPointF(x1, y1),
                    QPointF(x2, y2),
                ]
            )
        )


class QFlowChartView(QtW.QGraphicsView):
    item_left_clicked = QtCore.Signal(BaseNodeItem)
    item_right_clicked = QtCore.Signal(BaseNodeItem)
    background_left_clicked = QtCore.Signal(QtCore.QPointF)
    background_right_clicked = QtCore.Signal(QtCore.QPointF)

    def __init__(self, scene):
        super().__init__(scene)
        self._node_map = weakref.WeakValueDictionary[Hashable, QFlowChartNode]()
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        # Enable dragging the scene by dragging the background
        self._last_drag_position = QtCore.QPointF()

        self.horizontalScrollBar().hide()
        self.verticalScrollBar().hide()

    def add_child(
        self,
        item: BaseNodeItem,
        parents: list[QFlowChartNode] = [],
    ) -> QFlowChartNode:
        """Add a child node to the parents in the list"""
        parents = [
            p if isinstance(p, QFlowChartNode) else self._node_map[p] for p in parents
        ]
        if not parents:
            center = QtCore.QPointF(32, 24)
        else:
            # Calculate the center position based on the first parent
            xs = []
            ys = []
            for parent in parents:
                xs.append(parent.center().x())
                ys.append(parent.center().y() + parent.rect().height() / 2)
            child_x = min(xs)
            if len(xs) > 1 and np.std(xs) < 10:
                child_x += 32
            child_y = max(ys) + 45
            center = QtCore.QPointF(child_x, child_y)

        # shift to right if the position is already occupied
        need_shift = True
        while need_shift:
            for node in self._node_map.values():
                if node.rect().adjusted(-26, -20, 26, 20).contains(center):
                    center.setX(center.x() + node.rect().width() + 24)
                    break
            else:
                need_shift = False

        # Create the child node
        child_node = self.add_node(center, item)
        # Create arrows from each parent to the child
        for parent in parents:
            self.add_arrow(parent, child_node)
        return child_node

    def add_node(self, center: QtCore.QPointF, item: BaseNodeItem) -> QFlowChartNode:
        """Add a node to the scene at the specified center position"""
        node = QFlowChartNode(item, center.x(), center.y())
        self.scene().addItem(node)
        self._node_map[item.id()] = node
        node.setPen(QtGui.QPen(Qt.GlobalColor.black, 1.5))
        node.left_clicked.connect(self.item_left_clicked.emit)
        node.right_clicked.connect(self.item_right_clicked.emit)
        return node

    def add_arrow(self, start_node: QFlowChartNode, end_node: QFlowChartNode):
        """Add an arrow between two nodes"""
        arrow = QFlowChartArrow(start_node, end_node, color=self._arrow_color())
        arrow.setZValue(ZOrder.UNDERLAY)  # Ensure arrows are drawn below nodes
        self.scene().addItem(arrow)
        return arrow

    def _arrow_color(self) -> QtGui.QColor:
        if self.scene().backgroundBrush().color().lightness() < 128:
            arrow_color = QtGui.QColor(194, 194, 194)
        else:
            arrow_color = QtGui.QColor(62, 62, 62)
        return arrow_color

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Override mouse press event to start dragging the scene"""
        if _ := self.itemAt(event.pos()):
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and not self._last_drag_position.isNull()
        ):
            # If left button is pressed, drag the scene
            delta = event.position() - self._last_drag_position
            self._last_drag_position = event.position()
            for item in self.scene().items():
                if isinstance(item, QFlowChartNode):
                    item.setPos(item.pos() + delta)

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Override mouse release event to stop dragging the scene"""
        with suppress(RuntimeError):
            is_click = (
                self._last_drag_position - event.position()
            ).manhattanLength() < 4
            if event.button() == Qt.MouseButton.LeftButton:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                self._last_drag_position = QtCore.QPointF()
                if is_click:
                    # If it was a click, emit the background left clicked signal
                    self.background_left_clicked.emit(event.position())
            elif event.button() == Qt.MouseButton.RightButton:
                # If right button is released, emit the right clicked signal
                if is_click:
                    self.background_right_clicked.emit(event.position())
            return super().mouseReleaseEvent(event)


class QFlowChartSideView(QtW.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QtGui.QFont(MonospaceFontFamily, 9))
        self.setReadOnly(True)
        self.setLineWrapMode(QtW.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("Flow chart items will be displayed here.")


class QFlowChartWidget(QtW.QSplitter):
    def __init__(self):
        super().__init__(Qt.Orientation.Vertical)
        # Create graphics view and scene
        self.scene = QtW.QGraphicsScene()
        self.view = QFlowChartView(self.scene)
        self.side = QFlowChartSideView()
        self.addWidget(self.view)
        self.addWidget(self.side)
        self.setSizes([600, 200])

        self.view.item_left_clicked.connect(self._activate_item)
        self.view.background_left_clicked.connect(self._deactivate_item)

    def setBackgroundBrush(self, val):
        """Set the background brush of the scene"""
        self.scene.setBackgroundBrush(val)
        self.view.setBackgroundBrush(val)
        for item in self.scene.items():
            if isinstance(item, QFlowChartArrow):
                item.setPen(QtGui.QPen(self.view._arrow_color(), 1.2))

    def _activate_item(self, item: BaseNodeItem):
        """Handle item activation by displaying its content in the side view"""
        self.side.setPlainText(item.content())

    def _deactivate_item(self, pos: QtCore.QPointF):
        """Handle background click to clear the side view"""
        self.side.setPlainText("")


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    flowchart_widget = QFlowChartWidget()
    flowchart_widget.setWindowTitle("Flow Chart Example")
    flowchart_widget.resize(600, 400)
    flowchart_widget.show()
    app.exec()
