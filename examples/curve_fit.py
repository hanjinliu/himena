from functools import partial
import inspect
import numpy as np
from scipy import optimize
from himena import new_window, StandardType, WidgetDataModel, Parametric
from himena.plugins import register_function, configure_gui

@register_function(title="Curve fit ...")
def curve_fit() -> Parametric:
    @configure_gui(
        function={"types": StandardType.FUNCTION},
        xydata={"types": StandardType.DATAFRAME},
    )
    def run_fit(
        function: WidgetDataModel,
        xydata: WidgetDataModel,
        initial_guess: list[float],
    ) -> WidgetDataModel:
        func = function.value
        df = xydata.value
        xdata = df["x"]
        ydata = df["y"]
        if len(initial_guess) == 0:
            p0 = None
        else:
            p0 = initial_guess
        popt, _ = optimize.curve_fit(func, xdata, ydata, p0=p0)
        sig = inspect.signature(func)
        param_names = [param.name for param in sig.parameters.values()]
        param_names.pop(0)
        return WidgetDataModel(
            value=partial(func, **{k: float(v) for k, v in zip(param_names, popt)}),
            type=StandardType.FUNCTION_PARTIAL,
            title=function.title + " optimized"
        )
    return run_fit

def exponential_decay_model(x, k: float, a: float, b: float):
    return a * np.exp(-k * x) + b

def make_sample_data() -> WidgetDataModel:
    xdata = np.arange(100)
    ydata = exponential_decay_model(xdata, 0.1, 1, 0.5) + np.random.normal(0, 0.1, 100)
    return WidgetDataModel(
        value={"x": xdata, "y": ydata},
        type=StandardType.DATAFRAME,
        title="Sample data"
    )

if __name__ == "__main__":
    ui = new_window()
    ui.add_data_model(make_sample_data())
    ui.add_object(exponential_decay_model, type=StandardType.FUNCTION, title="exp func")
    ui.show(run=True)
