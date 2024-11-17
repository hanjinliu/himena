from typing import Annotated
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel


@register_function(
    menus=["tools/debug"],
    title="Just raise an exception",
)
def raise_exception():
    raise ValueError("This is a test exception")


@register_function(
    menus=["tools/debug"],
    title="Test model drop",
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
