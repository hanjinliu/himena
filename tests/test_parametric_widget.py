from typing import Annotated
from pathlib import Path
import pytest
from himena import WidgetDataModel, MainWindow

def test_parametric_simple(ui: MainWindow, tmpdir):
    ui.add_data("xyz", type="text")

    def func(a: int, b: float = 1.0, c: bool = False) -> WidgetDataModel[int]:
        return int(a + b) + int(c)

    win_ng = ui.add_function(func)
    with pytest.raises(ValueError):
        win_ng.to_model()  # "a" is missing

    def func_ok(a: int = -1, b: float = 1.0, c: bool = False) -> WidgetDataModel[int]:
        return int(a + b) + int(c)
    win_ok = ui.add_function(func_ok)
    assert win_ok.to_model().value == {"a": -1, "b": 1.0, "c": False}
    win_ok.write_model(Path(tmpdir / "test.json"))


def test_parametric_with_model(ui: MainWindow):
    def func(model: WidgetDataModel, a=2) -> WidgetDataModel[str]:
        return model.value * a

    win = ui.add_function(func)

def test_parametric_with_model_types(ui: MainWindow):
    def func(
        model: Annotated[WidgetDataModel, {"types": ["text"]}],
        a: tuple[int, int],
    ) -> WidgetDataModel[str]:
        return model.value * a[0] * a[1]
    ui.add_data("xyz", type="text")
    win = ui.add_function(func)

def test_custom_parametric_widget(ui: MainWindow):
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
    win = ui.add_parametric_widget(widget)
    widget._line.setText("xyz")
    assert win.get_params() == {"text": "xyz"}
    win._emit_btn_clicked()
    assert not win.is_alive
    with pytest.raises(TypeError):  # needs implementation of "is_preview_enabled" etc.
        ui.add_parametric_widget(widget, preview=True)

    class MyParams2(MyParams):
        def connect_changed_signal(self, callback):
            self._line.textChanged.connect(callback)

        def is_preview_enabled(self):
            return self._line.text() == "p"

    widget = MyParams2()
    win = ui.add_parametric_widget(widget, preview=True)
    widget._line.setText("x")
    assert win.get_params() == {"text": "x"}
    assert not win.is_preview_enabled()
    widget._line.setText("p")
    assert win.get_params() == {"text": "p"}
    assert win.is_preview_enabled()
    assert ui.tabs.current()[-1].to_model().value == "p"
