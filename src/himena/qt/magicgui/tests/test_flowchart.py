from cmap import Color
from himena.qt._qflowchart import QFlowChartWidget, TagItem, BaseNodeItem

class TestNodeItem(BaseNodeItem):
    def text(self) -> str:
        return "test"

    def color(self) -> Color:
        return Color("white")

    def tooltip(self) -> str:
        return "tooltip"

    def id(self):
        return id(self)

    def content(self) -> str:
        return "content"


def test_qflowchart_view(qtbot):
    widget = QFlowChartWidget()
    qtbot.addWidget(widget)
    flowchart_view = widget.view
    item0 = TestNodeItem()
    item1 = TestNodeItem()
    flowchart_view.add_child(item0)
    flowchart_view.add_child(item1, parents=[item0])

    # tags
    assert flowchart_view.tags() == []
    items = [TagItem("tag-1"), TagItem("tag-2")]
    flowchart_view.reset_tags(items)
    assert flowchart_view.tags()[0] is items[0]
    assert flowchart_view.tags()[1] is items[1]
    assert flowchart_view.item_tags(item0.id()) == []
    assert flowchart_view.item_tags(item1.id()) == []
    flowchart_view.set_item_tags(item0.id(), [items[0]])
    assert flowchart_view.item_tags(item0.id()) == [items[0]]
    assert flowchart_view.item_tags(item0.id())[0] is items[0]
    assert flowchart_view.item_tags(item1.id()) == []

    flowchart_view.edit_tag(0, "edited-tag-1")
    assert flowchart_view.item_tags(item0.id()) == [items[0]]
    assert items[0].name == "edited-tag-1"
