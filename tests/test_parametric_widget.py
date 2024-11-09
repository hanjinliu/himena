from himena import Parametric, WidgetDataModel, MainWindow

def test_parametric_simple(ui: MainWindow):
    def action_func() -> Parametric[int]:
        def func(a: int, b: float, c: bool) -> WidgetDataModel[int]:
            return int(a + b) + int(c)
        return func

    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(action_func)

def test_parametric_with_model_reference(ui: MainWindow):
    def action_func(model: WidgetDataModel[str]) -> Parametric[int]:
        def func(a: int) -> WidgetDataModel[str]:
            return model.value * a
        return func

    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(action_func)

def test_parametric_with_model_input(ui: MainWindow):
    def action_func() -> Parametric[int]:
        def func(
            m0: WidgetDataModel[str],
            m1: WidgetDataModel[str],
        ) -> WidgetDataModel[str]:
            return m0.value + m1.value
        return func

    ui.add_data("pqr", type="text")
    ui.add_data("xyz", type="text")
    win = ui.add_parametric_element(action_func)
