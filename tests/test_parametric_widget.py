from typing import Annotated
from pathlib import Path
import pytest
from himena import WidgetDataModel, MainWindow
from himena.consts import StandardType
from himena.qt.magicgui._toggle_switch import ToggleSwitch
from himena.qt._qparametric import QParametricWidget
from himena.widgets import SubWindow

def test_parametric_simple(himena_ui: MainWindow, tmpdir):
    himena_ui.add_object("xyz", type="text")

    def func(a: int, b: float = 1.0, c: bool = False) -> WidgetDataModel[int]:
        return int(a + b) + int(c)

    win_ng = himena_ui.add_function(func)
    with pytest.raises(ValueError):
        win_ng.to_model()  # "a" is missing

    def func_ok(a: int = -1, b: float = 1.0, c: bool = False) -> WidgetDataModel[int]:
        return int(a + b) + int(c)
    win_ok = himena_ui.add_function(func_ok)
    assert win_ok.to_model().value == {"a": -1, "b": 1.0, "c": False}
    win_ok.write_model(Path(tmpdir / "test.json"))


def test_parametric_with_model(himena_ui: MainWindow):
    def func(model: WidgetDataModel, a=2) -> WidgetDataModel[str]:
        return model.value * a

    win = himena_ui.add_function(func)

def test_parametric_with_model_types(himena_ui: MainWindow):
    def func(
        model: Annotated[WidgetDataModel, {"types": ["text"]}],
        a: tuple[int, int],
    ) -> WidgetDataModel[str]:
        return model.value * a[0] * a[1]
    himena_ui.add_object("xyz", type="text")
    win = himena_ui.add_function(func)

def test_parametric_str_output(himena_ui: MainWindow):
    def f(a: str = "xxxx") -> str:
        return a + "a"
    win = himena_ui.add_function(f, run_async=False)
    win._widget_callback()

def test_parametric_preview(himena_ui: MainWindow):
    def func(a: str = "a", is_previewing: bool = False) -> WidgetDataModel[int]:
        out = "preview" if is_previewing else a
        return WidgetDataModel(value=out, type=StandardType.TEXT)
    win = himena_ui.add_function(func, preview=True)
    assert not win.is_preview_enabled()
    assert isinstance(qwidget := win.widget, QParametricWidget)
    assert isinstance(toggle_switch := qwidget._central_widget[-1], ToggleSwitch)
    toggle_switch.value = True
    assert win.is_preview_enabled()
    assert isinstance(prev_win := win._preview_window_ref(), SubWindow)
    rect_prev = prev_win.rect
    toggle_switch.value = False
    assert not win.is_preview_enabled()
    toggle_switch.value = True
    win._widget_callback()  # call the function

def test_custom_parametric_widget(himena_ui: MainWindow):
    from qtpy import QtWidgets as QtW

    class MyParams(QtW.QWidget):
        def __init__(self):
            super().__init__()
            layout = QtW.QVBoxLayout(self)
            self._line = QtW.QLineEdit()
            layout.addWidget(self._line)

        def get_params(self):
            return {"text": self._line.text()}

        def get_output(self, text: str):
            return WidgetDataModel(value=text, type="text")

    widget = MyParams()
    win = himena_ui.add_parametric_widget(widget)
    widget._line.setText("xyz")
    assert win.get_params() == {"text": "xyz"}
    win._emit_btn_clicked()
    assert not win.is_alive
    with pytest.raises(TypeError):  # needs implementation of "is_preview_enabled" etc.
        himena_ui.add_parametric_widget(widget, preview=True)

    class MyParams2(MyParams):
        def connect_changed_signal(self, callback):
            self._line.textChanged.connect(callback)

        def is_preview_enabled(self):
            return self._line.text() == "p"

    widget = MyParams2()
    win = himena_ui.add_parametric_widget(widget, preview=True)
    widget._line.setText("x")
    assert win.get_params() == {"text": "x"}
    assert not win.is_preview_enabled()
    widget._line.setText("p")
    assert win.get_params() == {"text": "p"}
    assert win.is_preview_enabled()
    assert himena_ui.tabs.current()[-1].to_model().value == "p"
