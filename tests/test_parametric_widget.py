from typing import Annotated
from himena import WidgetDataModel, MainWindow

def test_parametric_simple(ui: MainWindow):
    def func(a: int, b: float, c: bool) -> WidgetDataModel[int]:
        return int(a + b) + int(c)

    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(func)

def test_parametric_with_model(ui: MainWindow):
    def func(model: WidgetDataModel, a: int) -> WidgetDataModel[str]:
        return model.value * a

    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(func)

def test_parametric_with_model_types(ui: MainWindow):
    def func(
        model: Annotated[WidgetDataModel, {"types": ["text"]}],
        a: tuple[int, int],
    ) -> WidgetDataModel[str]:
        return model.value * a[0] * a[1]
    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(func)
