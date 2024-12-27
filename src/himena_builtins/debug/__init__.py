import time
from typing import Annotated
import numpy as np
from himena.consts import StandardType
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel, WidgetConstructor
from himena.widgets import MainWindow, notify, set_status_tip

TOOLS_DEBUG = "tools/debug"


@register_function(
    menus=TOOLS_DEBUG,
    title="Just raise an exception",
    command_id="debug:raise-exception",
)
def raise_exception():
    raise ValueError("This is a test exception")


@register_function(
    menus=TOOLS_DEBUG,
    title="Just warn",
    command_id="debug:warning",
)
def raise_warning():
    import warnings

    warnings.warn("This is a test warning", UserWarning, stacklevel=2)


@register_function(
    menus=TOOLS_DEBUG,
    title="Raise when warning",
    command_id="debug:raise-when-warning",
)
def raise_when_warning():
    import warnings

    warnings.simplefilter("error")


@register_function(
    menus=TOOLS_DEBUG,
    title="Test model drop",
    command_id="debug:test-model-drop",
)
def function_with_model_drop() -> Parametric:
    def run(
        model_any: WidgetDataModel,
        model_text: Annotated[WidgetDataModel[str], {"types": "text"}],
        model_image: Annotated[WidgetDataModel, {"types": "array.image"}],
    ):
        print(model_any)
        print(model_text)
        print(model_image)

    return run


@register_function(
    menus=TOOLS_DEBUG,
    title="Open User Preferences",
    command_id="debug:open-user-preferences",
)
def open_user_preferences(ui: MainWindow):
    from himena.profile import data_dir, profile_dir

    output = []
    for path in profile_dir().glob("*.json"):
        output.append(path)
    output.append(data_dir() / "recent.json")
    output.append(data_dir() / "recent_sessions.json")
    ui.read_files(output)
    return None


@register_function(
    menus=TOOLS_DEBUG,
    title="Test preview",
    command_id="debug:test-preview",
)
def preview_test() -> Parametric:
    @configure_gui(preview=True)
    def testing_preview(a: int, b: str, is_previewing: bool = False) -> WidgetDataModel:
        out = f"a = {a!r}\nb ={b!r}"
        if is_previewing:
            out += "\n(preview)"
        print(f"called with {a=}, {b=}, {is_previewing=}")
        return WidgetDataModel(value=out, type=StandardType.TEXT)

    return testing_preview


@register_function(
    menus=TOOLS_DEBUG,
    title="Test plot",
    command_id="debug:test-plot",
)
def plot_test() -> Parametric:
    import himena.standards.plotting as hplt

    @configure_gui(preview=True)
    def run(a: int, b: int = 4) -> WidgetDataModel:
        fig = hplt.figure()
        fig.axes.plot([0, 1, 2], [2, a, b], color="red")
        fig.axes.title = "Test plot"
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return run


@register_function(
    menus=TOOLS_DEBUG,
    title="Test plot with parametric (below)",
    command_id="debug:test-plot-parametric-below",
)
def plot_test_parametric_below() -> Parametric:
    import himena.standards.plotting as hplt

    @configure_gui(preview=True, result_as="below")
    def run(freq: float = 1.0, phase: float = 0.0) -> WidgetDataModel:
        fig = hplt.figure()
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(freq * x + phase)
        fig.axes.plot(x, y, color="red")
        fig.axes.title = "Test plot"
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return run


@register_function(
    menus=TOOLS_DEBUG,
    title="Test plot with parametric (right)",
    command_id="debug:test-plot-parametric-right",
)
def plot_test_parametric_right() -> Parametric:
    import himena.standards.plotting as hplt

    @configure_gui(preview=True, result_as="right")
    def run(freq: float = 1.0, phase: float = 0.0) -> WidgetDataModel:
        fig = hplt.figure()
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(freq * x + phase)
        fig.axes.plot(x, y, color="red")
        fig.axes.title = "Test plot"
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return run


@register_function(
    menus=TOOLS_DEBUG,
    title="Test async checkpoints",
    command_id="debug:test-async-checkpoints",
)
def test_async_checkpoints() -> Parametric:
    import time

    @configure_gui(run_async=True)
    def run():
        for i in range(10):
            time.sleep(0.3)
        return

    return run


@register_function(
    menus=TOOLS_DEBUG,
    title="Test async widget creation",
    command_id="debug:test-async-widget-creation",
)
def test_async_widget_creation() -> Parametric:
    from magicgui.widgets import Container, LineEdit

    def make_widget(texts: list[str]):
        con = Container()
        for text in texts:
            con.append(LineEdit(value=text))
        return con.native

    @configure_gui(run_async=True)
    def run() -> WidgetConstructor:
        texts = []
        for i in range(10):
            time.sleep(0.3)
            texts.append(f"Text {i}")
        return lambda: make_widget(texts)

    return run


@register_function(
    menus=TOOLS_DEBUG,
    title="Test notification",
    command_id="debug:test-notification",
)
def test_notification() -> Parametric:
    @configure_gui(run_async=True)
    def run(notification: bool = True, status_tip: bool = True):
        time.sleep(1)
        if status_tip:
            notify("1. This is test notification", duration=4.2)
        if notification:
            set_status_tip("1. This is test status tip", duration=4.2)
        time.sleep(1)
        if status_tip:
            notify("2. This is test notification", duration=4.2)
        if notification:
            set_status_tip("2. This is test status tip", duration=4.2)

    return run
