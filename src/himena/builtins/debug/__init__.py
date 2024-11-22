from pathlib import Path
from typing import Annotated
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel

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
def open_user_preferences() -> list[Path]:
    from himena.profile import data_dir, profile_dir

    output = []
    for path in profile_dir().glob("*.json"):
        output.append(path)
    output.append(data_dir() / "recent.json")
    output.append(data_dir() / "recent_sessions.json")
    return output


@register_function(
    menus=TOOLS_DEBUG,
    title="Test preview",
    command_id="debug:test-preview",
    preview=True,
)
def preview_test() -> Parametric:
    def testing_preview(a: int, b: str, is_previewing: bool = False) -> WidgetDataModel:
        out = f"a = {a!r}\nb ={b!r}"
        if is_previewing:
            out += "\n(preview)"
        print(f"called with {a=}, {b=}, {is_previewing=}")
        return WidgetDataModel(value=out, type="text")

    return testing_preview


@register_function(
    menus=TOOLS_DEBUG,
    title="Test plot",
    command_id="debug:test-plot",
    preview=True,
)
def plot_test() -> Parametric:
    import himena.plotting as hplt

    def run(a: int, b: int = 4) -> WidgetDataModel:
        fig = hplt.figure()
        fig.axes.plot([0, 1, 2], [2, a, b], color="red")
        fig.axes.title = "Test plot"
        return WidgetDataModel(value=fig, type="matplotlib-figure")

    return run
