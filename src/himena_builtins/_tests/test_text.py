from pathlib import Path
from qtpy import QtGui
from qtpy.QtCore import Qt
from himena import MainWindow, StandardType
from himena.standards.model_meta import TextMeta
from himena.types import WidgetDataModel
from himena_builtins.qt.text import QTextEdit, QRichTextEdit, QSvgPreview, QMarkdowPreview
from pytestqt.qtbot import QtBot
from himena.testing import WidgetTester

_Ctrl = Qt.KeyboardModifier.ControlModifier


def test_text_edit(qtbot: QtBot):
    model = WidgetDataModel(value="a\nb", type="text")
    with WidgetTester(QTextEdit()) as tester:
        tester.update_model(model)
        qtbot.addWidget(tester.widget)
        main = tester.widget._main_text_edit

        assert tester.to_model().value == "a\nb"
        assert main.toPlainText() == "a\nb"
        # move to the end
        cursor = main.textCursor()
        cursor.setPosition(len(main.toPlainText()))
        main.setTextCursor(cursor)

        qtbot.keyClick(main, Qt.Key.Key_Return)
        qtbot.keyClick(main, Qt.Key.Key_Tab)
        qtbot.keyClick(main, Qt.Key.Key_Backtab)
        qtbot.keyClick(main, Qt.Key.Key_Tab)
        qtbot.keyClick(main, Qt.Key.Key_O)
        qtbot.keyClick(main, Qt.Key.Key_P)
        assert tester.to_model().value.splitlines() == ["a", "b", "    op"]
        qtbot.keyClick(main, Qt.Key.Key_Home)
        qtbot.keyClick(main, Qt.Key.Key_Up, modifier=Qt.KeyboardModifier.AltModifier)
        qtbot.keyClick(main, Qt.Key.Key_Down, modifier=Qt.KeyboardModifier.AltModifier)
        qtbot.keyClick(main, Qt.Key.Key_Down)
        qtbot.keyClick(main, Qt.Key.Key_Down)
        qtbot.keyClick(main, Qt.Key.Key_Down)
        qtbot.keyClick(main, Qt.Key.Key_Tab)
        qtbot.keyClick(main, Qt.Key.Key_X)
        qtbot.keyClick(main, Qt.Key.Key_Return)
        qtbot.keyClick(main, Qt.Key.Key_A)
        qtbot.keyClick(main, Qt.Key.Key_B)
        qtbot.keyClick(main, Qt.Key.Key_C)
        qtbot.keyClick(main, Qt.Key.Key_D)
        qtbot.keyClick(main, Qt.Key.Key_L, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_Up, modifier=Qt.KeyboardModifier.AltModifier)
        qtbot.keyClick(main, Qt.Key.Key_Down, modifier=Qt.KeyboardModifier.AltModifier)
        qtbot.keyClick(main, Qt.Key.Key_Left)
        qtbot.keyClick(main, Qt.Key.Key_D, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_C, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_Return)
        qtbot.keyClick(main, Qt.Key.Key_V, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_Less, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_Greater, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_Greater, modifier=_Ctrl)
        qtbot.keyClick(main, Qt.Key.Key_0, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_F, modifier=_Ctrl)
        tester.widget.resize(100, 100)
        tester.widget.resize(120, 120)


def test_find_text(qtbot: QtBot):
    model = WidgetDataModel(value="a\nb\nc\nbc", type="text")
    text_edit = QTextEdit()
    text_edit.update_model(model)
    qtbot.addWidget(text_edit)
    qtbot.keyClick(text_edit, Qt.Key.Key_F, modifier=_Ctrl)
    finder = text_edit._main_text_edit._finder_widget
    assert finder is not None
    finder._line_edit.setText("b")
    qtbot.keyClick(finder, Qt.Key.Key_Enter)
    qtbot.keyClick(finder, Qt.Key.Key_Enter, modifier=Qt.KeyboardModifier.ShiftModifier)
    finder._btn_next.click()
    finder._btn_prev.click()

def test_svg_preview(sample_dir: Path, qtbot):
    with WidgetTester(QSvgPreview()) as tester:
        svg_path = sample_dir / "svg.svg"
        tester.update_model(value=svg_path.read_text(), type=StandardType.SVG)
        tester.to_model()

def test_markdow_preview(sample_dir: Path, qtbot):
    with WidgetTester(QMarkdowPreview()) as tester:
        md_path = sample_dir / "markdown.md"
        tester.update_model(value=md_path.read_text(), type=StandardType.MARKDOWN)
        tester.to_model()

def test_rich_text(sample_dir: Path, qtbot):
    with WidgetTester(QRichTextEdit()) as tester:
        md_path = sample_dir / "html.html"
        tester.update_model(value=md_path.read_text(), type=StandardType.HTML)
        tester.to_model()
        tester.widget._control._on_foreground_color_changed(QtGui.QColor("blue"))
        tester.widget._control._on_background_color_changed(QtGui.QColor("red"))
        tester.widget._control._on_toggle_bold()
        tester.widget._control._on_toggle_italic()
        tester.widget._control._on_toggle_underline()
        tester.widget._control._on_toggle_strike()

def test_commands(himena_ui: MainWindow):
    win = himena_ui.add_object("print(2)", type=StandardType.TEXT)
    win.update_model(win.to_model().with_metadata(TextMeta(language="python")))
    himena_ui.exec_action("builtins:text-run:run-script")
    win = himena_ui.add_object("1,2,3", type=StandardType.TEXT)
    himena_ui.exec_action("builtins:text:change-separator", with_params={})
    assert himena_ui.current_model.value == "1\t2\t3"
    himena_ui.exec_action("builtins:text:change-encoding", with_params={"encoding": "utf-16"})
    assert himena_ui.current_model.metadata.encoding == "utf-16"
    himena_ui.add_object("def f(x):\n    return x + 1", type=StandardType.TEXT)
    himena_ui.exec_action("builtins:text-run:compile-as-function")
    himena_ui.add_object("def f(x):\n    return x + 1\nf", type=StandardType.TEXT)
    himena_ui.exec_action("builtins:text-run:compile-as-function")
    himena_ui.add_object("def main(x):\n    return x\n", type=StandardType.TEXT)
    himena_ui.exec_action("builtins:text-run:run-script-main", with_params={"x": himena_ui.tabs[0][0]})

def test_open_as_text_anyway(sample_dir: Path, himena_ui: MainWindow):
    himena_ui.read_file(sample_dir / "random_ext.aaa")
    assert himena_ui.current_model.type == StandardType.READER_NOT_FOUND
    himena_ui.exec_action("builtins:open-as-text-anyway")
    assert len(himena_ui.tabs[0]) == 1
    assert himena_ui.current_model.type == StandardType.TEXT
    assert himena_ui.current_model.value == sample_dir.joinpath("random_ext.aaa").read_text()
    assert himena_ui.current_model.extension_default == ".aaa"
