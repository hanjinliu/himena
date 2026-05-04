from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
import math
from typing import Hashable, Iterable, Iterator
import uuid
import weakref
import numpy as np
from psygnal import Signal
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, QPointF
from cmap import Color
from himena.consts import MonospaceFontFamily, DefaultFontFamily


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

    @abstractmethod
    def content(self) -> str:
        """Return the content of the node, default is the text"""


@dataclass(frozen=True)
class TagItem:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    color: Color = field(default=Color([255, 30, 30]))
    tooltip: str = ""

    def __post_init__(self):
        object.__setattr__(self, "color", Color(self.color))
        if not self.tooltip:
            object.__setattr__(self, "tooltip", self.name)

    @classmethod
    def default(cls):
        return cls(name="Default", color=Color([0, 0, 0]), id=uuid.UUID(int=0))


class ZOrder(IntEnum):
    UNDERLAY = -100
    OVERLAY = 100


class QFlowChartNode(QtW.QGraphicsRectItem):
    left_pressed = Signal(object)
    right_pressed = Signal(object)
    left_clicked = Signal(object)
    left_double_clicked = Signal(object)
    right_clicked = Signal(object)
    right_double_clicked = Signal(object)

    def __init__(self, item: BaseNodeItem, x: float = 0.0, y: float = 0.0):
        super().__init__(0, 0, 1, 1)
        self._item = item  # Store the item associated with this node
        # List of arrows connected to this node
        self._connected_arrows_from: list[QFlowChartArrow] = []
        self._connected_arrows_to: list[QFlowChartArrow] = []
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
        font = QtGui.QFont(DefaultFontFamily, 9)
        self.text_item.setFont(font)

        # Add tag item pointing at the top-right corner
        self.tag_items: list[QFlowChartTag] = []

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

    def _update_tag_position(self):
        """Position the tag at the top-right corner of the node"""
        tag_origin = self.rect().topRight() - QPointF(3, 3)
        for tag_item in self.tag_items:
            tag_item.setPos(tag_origin)
            tag_origin.setX(tag_origin.x() + tag_item.boundingRect().width() * 0.67)

    def add_arrow_from(self, arrow):
        """Add an arrow to the list of connected arrows from other nodes to this."""
        if arrow not in self._connected_arrows_to:
            self._connected_arrows_to.append(arrow)

    def add_arrow_to(self, arrow):
        """Add an arrow to the list of connected arrows from this node to another"""
        if arrow not in self._connected_arrows_from:
            self._connected_arrows_from.append(arrow)

    def remove_arrow(self, arrow):
        """Remove an arrow from the list of connected arrows"""
        if arrow in self._connected_arrows_from:
            self._connected_arrows_from.remove(arrow)
        if arrow in self._connected_arrows_to:
            self._connected_arrows_to.remove(arrow)

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
            for arrow in self._connected_arrows_from + self._connected_arrows_to:
                arrow._update_position()
            self._update_text_position()
            self._update_tag_position()
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

    def edit_tag(
        self,
        index: int,
        name: str | None = None,
        color: Color | None = None,
        tooltip: str | None = None,
    ):
        if 0 <= index < len(self.tag_items):
            qtab = self.tag_items[index]
            cur_tab = qtab._tag_item
            tag = TagItem(
                name=name or cur_tab.name,
                color=color or cur_tab.color,
                tooltip=tooltip or cur_tab.tooltip,
                id=cur_tab.id,
            )
            qtab.set_tag_item(tag)

    def set_tags(self, tags: list[TagItem]):
        if len(tags) < len(self.tag_items):
            for qtag in self.tag_items[len(tags) :]:
                qtag.setParentItem(None)
            self.tag_items = self.tag_items[: len(tags)]
        elif len(tags) > len(self.tag_items):
            for _ in range(len(tags) - len(self.tag_items)):
                qtag = QFlowChartTag(self)
                self.tag_items.append(qtag)
        for qtag, tag in zip(self.tag_items, tags):
            qtag.set_tag_item(tag)
        self._update_tag_position()

    def mousePressEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        """Handle mouse press events"""
        self._last_press_pos = self.mapFromScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_pressed.emit(self._item)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_pressed.emit(self._item)
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        """Handle mouse release events"""
        super().mouseReleaseEvent(event)
        if (
            self._last_press_pos - self.mapFromScene(event.pos())
        ).manhattanLength() < 4:
            if event.button() == Qt.MouseButton.LeftButton:
                self.left_clicked.emit(self._item)
            elif event.button() == Qt.MouseButton.RightButton:
                self.right_clicked.emit(self._item)
        self._last_press_pos = QtCore.QPointF()

    def mouseDoubleClickEvent(self, event):
        """Handle mouse double click events"""
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_double_clicked.emit(self._item)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_double_clicked.emit(self._item)


class QFlowChartArrow(QtW.QGraphicsLineItem):
    """An path item with an arrowhead.

    `offset` is used to shift the arrow line when multiple arrows may overlap.
    """

    def __init__(
        self,
        start_node: QFlowChartNode,
        end_node: QFlowChartNode,
        color: QtGui.QColor = Qt.GlobalColor.black,
        offset: int = 0,
    ):
        super().__init__()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.start_node = start_node
        self.end_node = end_node
        self.arrowhead_size = 10
        self.offset = offset
        self.arrowhead = QtW.QGraphicsPolygonItem(self)
        self.set_color(color)

        # Register this arrow with both nodes
        # start --> end
        self.start_node.add_arrow_to(self)
        self.end_node.add_arrow_from(self)

        # Initial position update
        self._update_position()

    def set_color(self, color: QtGui.QColor):
        pen = QtGui.QPen(color, 1.2)

        # Set line properties
        self.setPen(pen)

        # Create arrowhead as a separate graphics item
        # Arrowhead as a triangle polygon
        pen.setJoinStyle(Qt.PenJoinStyle.SvgMiterJoin)
        self.arrowhead.setBrush(QtGui.QBrush(color))
        self.arrowhead.setPen(pen)

    def _update_position(self):
        """Update the arrow position based on the connected nodes"""
        # Get the edge points of both nodes
        start_center = self.start_node.center()
        end_center = self.end_node.center()

        start_point = self.start_node._get_edge_point(end_center)
        end_point = self.end_node._get_edge_point(start_center)

        # Apply offset
        offset_val = self.offset * 3
        start_point.setX(start_point.x() + offset_val)
        end_point.setX(end_point.x() + offset_val)

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
            QtGui.QPolygonF([end_point, QPointF(x1, y1), QPointF(x2, y2)])
        )


class QFlowChartTag(QtW.QGraphicsPolygonItem):
    def __init__(self, parent):
        _tag_size = 10
        polygon = QtGui.QPolygonF(
            [
                QPointF(0, _tag_size),
                QPointF(0, _tag_size / 2),
                QPointF(_tag_size / 2, 0),
                QPointF(_tag_size, _tag_size / 2),
                QPointF(_tag_size / 2, _tag_size),
            ]
        )
        super().__init__(polygon, parent)
        _tag_pen = QtGui.QPen(Qt.GlobalColor.black, 1)
        _tag_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(_tag_pen)
        self._tag_item = TagItem.default()
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_tag_item(self, tag: TagItem):
        self._tag_item = tag
        color = QtGui.QColor.fromRgbF(*tag.color.rgba)
        pen = self.pen()
        pen.setColor(color)
        brush_color = pen.color()
        brush_color.setAlpha(180)

        self.setPen(pen)
        self.setBrush(brush_color)
        self.setToolTip(tag.tooltip)


class QFlowChartView(QtW.QGraphicsView):
    item_left_pressed = QtCore.Signal(BaseNodeItem)
    item_right_pressed = QtCore.Signal(BaseNodeItem)
    item_left_clicked = QtCore.Signal(BaseNodeItem)
    item_right_clicked = QtCore.Signal(BaseNodeItem)
    item_left_double_clicked = QtCore.Signal(BaseNodeItem)
    item_right_double_clicked = QtCore.Signal(BaseNodeItem)
    background_left_clicked = QtCore.Signal(QtCore.QPointF)
    background_right_clicked = QtCore.Signal(QtCore.QPointF)

    def __init__(self, scene):
        super().__init__(scene)
        self._node_map = weakref.WeakValueDictionary[Hashable, QFlowChartNode]()
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        # Enable dragging the scene by dragging the background
        self._last_drag_position = QtCore.QPointF()
        self._move_delta = QPointF(0, 0)

        self.horizontalScrollBar().hide()
        self.verticalScrollBar().hide()

        self._dodge_distance = 32
        self._tag_collection: list[TagItem] = []

    def add_child(
        self,
        item: BaseNodeItem,
        parents: list[Hashable | QFlowChartNode] = [],
    ) -> QFlowChartNode:
        """Add a child node to the parents in the list"""
        parent_nodes: list[QFlowChartNode] = []
        for p in parents:
            if isinstance(p, QFlowChartNode):
                parent_nodes.append(p)
            elif p in self._node_map:
                # NOTE: in the subclasses, probably not all nodes are added.
                parent_nodes.append(self._node_map[p])
        if not parent_nodes:
            center = QtCore.QPointF(32, 24)
        else:
            # Calculate the center position based on the first parent
            xs: list[float] = []
            ys: list[float] = []
            for parent in parent_nodes:
                xs.append(parent.center().x())
                ys.append(parent.center().y() + parent.rect().height() / 2)
            child_x = np.mean(xs)
            child_y = max(ys) + 45
            center = QtCore.QPointF(child_x, child_y)

        # shift to left or right if the position is already occupied
        center = find_unoccupied_position(
            center,
            list(self._node_map.values()),
            self._dodge_distance,
        )

        # Create the child node
        child_node = self.add_node(center, item)
        # Create arrows from each parent to the child
        for parent in parent_nodes:
            self.add_arrow(parent, child_node)
        return child_node

    def add_node(self, center: QtCore.QPointF, item: BaseNodeItem) -> QFlowChartNode:
        """Add a node to the scene at the specified center position"""
        node = QFlowChartNode(item, center.x(), center.y())
        self.scene().addItem(node)
        self._node_map[item.id()] = node
        node.setPen(QtGui.QPen(Qt.GlobalColor.black, 1.5))

        # connect events
        node.left_pressed.connect(self.item_left_pressed.emit)
        node.right_pressed.connect(self.item_right_pressed.emit)
        node.left_clicked.connect(self.item_left_clicked.emit)
        node.right_clicked.connect(self.item_right_clicked.emit)
        node.left_double_clicked.connect(self.item_left_double_clicked.emit)
        node.right_double_clicked.connect(self.item_right_double_clicked.emit)
        return node

    def add_arrow(self, start_node: QFlowChartNode, end_node: QFlowChartNode):
        """Add an arrow between two nodes"""
        ith = len(start_node._connected_arrows_from) - 1
        offset_sign = -1 if ith % 2 == 0 else 1
        arrow = QFlowChartArrow(
            start_node,
            end_node,
            color=self._arrow_color(ith),
            offset=offset_sign * (ith + 1) // 2,
        )
        arrow.setZValue(ZOrder.UNDERLAY)  # Ensure arrows are drawn below nodes
        self.scene().addItem(arrow)
        return arrow

    def remove_nodes(self, nodes: Iterable[QFlowChartNode]):
        """Remove nodes and their associated arrows from the scene"""
        for node in nodes:
            # Remove all arrows connected to this node
            for arrow in node._connected_arrows_from + node._connected_arrows_to:
                self.scene().removeItem(arrow)
                node.remove_arrow(arrow)
            # Remove the node itself
            self.scene().removeItem(node)
            self._node_map.pop(node.item().id(), None)

    def tags(self) -> list[TagItem]:
        """List of all tags in the flow chart"""
        return list(self._tag_collection)

    def reset_tags(self, tags: list[TagItem]):
        """Reset the tag collection and update all nodes accordingly"""
        self._tag_collection = tags
        self._update_ui_by_current_tags()

    def item_tags(self, item_id: Hashable) -> list[TagItem]:
        """Get the tags associated with a specific item by its ID"""
        if node := self._node_map.get(item_id):
            return [qtag._tag_item for qtag in node.tag_items]
        return []

    def set_item_tags(self, item_id: Hashable, tags: list[TagItem]):
        if node := self._node_map.get(item_id):
            node.set_tags(tags)

    def edit_tag(
        self,
        index: int,
        name: str | None = None,
        color: Color | None = None,
        tooltip: str | None = None,
    ):
        if index < 0:
            # create new tag
            name = name or f"Tag {len(self._tag_collection)}"
            tag = TagItem(
                name=name,
                color=color or Color([255, 30, 30]),
                tooltip=tooltip or name,
            )
            self._tag_collection.append(tag)
        else:
            old_tag = self._tag_collection[index]
            self._tag_collection[index] = TagItem(
                name=name or old_tag.name,
                id=old_tag.id,
                color=color or old_tag.color,
                tooltip=tooltip or old_tag.tooltip,
            )
        self._update_ui_by_current_tags()

    def _update_ui_by_current_tags(self):
        id_to_tag_map = {tag.id: tag for tag in self._tag_collection}
        for node in self._node_map.values():
            new_tags: list[TagItem] = []
            for qtag in node.tag_items:
                tag_id = qtag._tag_item.id
                if tag := id_to_tag_map.get(tag_id):
                    new_tags.append(tag)
            node.set_tags(new_tags)

    def list_ids(self) -> list[Hashable]:
        """List all node IDs in the flow chart"""
        return list(self._node_map.keys())

    def item(self, item_id: Hashable) -> BaseNodeItem | None:
        """Get the associated item by its ID"""
        if node := self._node_map.get(item_id):
            return node.item()

    def setBackgroundBrush(self, val):
        super().setBackgroundBrush(val)
        for node in self._node_map.values():
            for ith, arrow in enumerate(node._connected_arrows_from):
                arrow.set_color(self._arrow_color(ith))

    def _arrow_color(self, ith: int = 0) -> QtGui.QColor:
        if self.scene().backgroundBrush().color().lightness() < 128:
            base_lightness = 194
        else:
            base_lightness = 62

        # Calculate hue based on ith (distribute colors around the color wheel)
        hue = (ith * 137) % 360
        saturation = 128  # Moderate saturation for visible color variation
        arrow_color = QtGui.QColor.fromHsl(hue, saturation, base_lightness)
        return arrow_color

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Override mouse press event to start dragging the scene"""
        if _ := self.itemAt(event.pos()):
            return super().mousePressEvent(event)
        self._last_drag_position = event.position()
        self._move_delta = QPointF(0, 0)
        if event.button() == Qt.MouseButton.LeftButton:
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
            self._move_delta += delta
            for item in self.scene().items():
                if isinstance(item, QFlowChartNode):
                    item.setPos(item.pos() + delta)

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Override mouse release event to stop dragging the scene"""
        if self._last_drag_position.isNull():
            return super().mouseReleaseEvent(event)
        is_click = self._move_delta.manhattanLength() < 4
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

    def mouseDoubleClickEvent(self, event):
        self._last_drag_position = QtCore.QPointF()
        return super().mouseDoubleClickEvent(event)


def iter_next_shift(stride: float, max_value: float = 1e4) -> Iterator[float]:
    """Yield next shift in ... 4, 2, 0, 1, 3 ... order."""
    yield 0.0
    cur_stride = stride
    while True:
        for direction in (1, -1):
            yield direction * cur_stride
        cur_stride += stride
        if cur_stride > max_value:
            # just for safety
            raise StopIteration


def find_unoccupied_position(
    center: QtCore.QPointF,
    nodes: list[QFlowChartNode],
    dodge_distance: float = 32,
):
    # list of nodes that has similar y value
    may_overlap = [node for node in nodes if abs(node.center().y() - center.y()) < 20]
    if not may_overlap:
        return center
    x_val_occupied: list[tuple[float, float]] = []
    for node in may_overlap:
        rect = node.rect()
        left = rect.left() - dodge_distance + 6
        right = rect.right() + dodge_distance - 6
        x_val_occupied.append((left, right))

    def is_ok(x: float) -> bool:
        for left, right in x_val_occupied:
            if left <= x <= right:
                return False
        return True

    it = iter_next_shift(dodge_distance)
    current_shift = next(it)
    while not is_ok(center.x() + current_shift):
        current_shift = next(it)
    center.setX(center.x() + current_shift)
    return center


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

    def _activate_item(self, item: BaseNodeItem):
        """Handle item activation by displaying its content in the side view"""
        self.side.setPlainText(item.content())

    def _deactivate_item(self, pos: QtCore.QPointF):
        """Handle background click to clear the side view"""
        self.side.setPlainText("")
