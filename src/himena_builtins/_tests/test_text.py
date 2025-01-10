from pathlib import Path
from qtpy import QtGui
from himena.consts import StandardType
from himena.testing import WidgetTester
from himena_builtins.qt.widgets.text import QRichTextEdit
from himena_builtins.qt.widgets.text_previews import QSvgPreview, QMarkdowPreview

def test_svg_preview(sample_dir: Path, qtbot):
    tester = WidgetTester(QSvgPreview())
    svg_path = sample_dir / "svg.svg"
    tester.update_model(value=svg_path.read_text(), type=StandardType.SVG)
    tester.to_model()
    tester.test_callbacks()

def test_markdow_preview(sample_dir: Path, qtbot):
    tester = WidgetTester(QMarkdowPreview())
    md_path = sample_dir / "markdown.md"
    tester.update_model(value=md_path.read_text(), type=StandardType.MARKDOWN)
    tester.to_model()
    tester.test_callbacks()

def test_rich_text(sample_dir: Path, qtbot):
    tester = WidgetTester(QRichTextEdit())
    md_path = sample_dir / "html.html"
    tester.update_model(value=md_path.read_text(), type=StandardType.HTML)
    tester.to_model()
    tester.test_callbacks()
    tester.widget._control._on_foreground_color_changed(QtGui.QColor("blue"))
    tester.widget._control._on_background_color_changed(QtGui.QColor("red"))
    tester.widget._control._on_toggle_bold()
    tester.widget._control._on_toggle_italic()
    tester.widget._control._on_toggle_underline()
    tester.widget._control._on_toggle_strike()
