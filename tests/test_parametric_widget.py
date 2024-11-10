from typing import Annotated

import pytest
from himena import WidgetDataModel, MainWindow

def test_parametric_simple(ui: MainWindow):
    ui.add_data("xyz", type="text")

    def func(a: int, b: float = 1.0, c: bool = False) -> WidgetDataModel[int]:
        return int(a + b) + int(c)

    win = ui.add_parametric_element(func)
    with pytest.raises(ValueError):
        win.to_model()  # "a" is missing

    def func_ok(a: int = -1, b: float = 1.0, c: bool = False) -> WidgetDataModel[int]:
        return int(a + b) + int(c)
    win_ok = ui.add_parametric_element(func_ok)
    assert win_ok.to_model().value == {"a": -1, "b": 1.0, "c": False}


def test_parametric_with_model(ui: MainWindow):
    def func(model: WidgetDataModel, a=2) -> WidgetDataModel[str]:
        return model.value * a

    win = ui.add_parametric_element(func)

def test_parametric_with_model_types(ui: MainWindow):
    def func(
        model: Annotated[WidgetDataModel, {"types": ["text"]}],
        a: tuple[int, int],
    ) -> WidgetDataModel[str]:
        return model.value * a[0] * a[1]
    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(func)
