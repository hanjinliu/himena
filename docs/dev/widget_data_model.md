# The WidgetDataModel Standard

All the widgets in `himena` are built on the `WidgetDataModel` standard. A
`WidgetDataModel` is a Python object that represents a value of any type, tagged with
some additional information of how to interpret the value in GUI. For example, a text
data "xyz" read from a txt file can be written as follows:

``` python
WidgetDataModel(value="abc", type="text")
```

All the "data-embedded" widgets in `himena` implements `update_model()` method to update
the state of the widget from a `WidgetDataModel` object, and `to_model()` method to dump
the state of the widget to a `WidgetDataModel` object.

``` python
class TextViewer:
    def __init__(self):
        # some GUI-specific initialization ...

    def update_model(self, model: WidgetDataModel):
        self.set_text(model.value)  # (1)!

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self.get_text(), type="text")  # (2)!
```

(1) The incoming text data is stored in `model.value`. The `set_text()` method is just
    an example.
(2) A `WidgetDataModel` must be returned here. The "text" type is the standard type
    string for the string-type text data.

This widget can be registered as a widget that represents a `"text"`-type data using
`register_widget_class()` function.

``` python
from himena.plugins import register_widget_class

register_widget_class("text", widget_class=TextViewer)
```

The `WidgetDataModel` standard makes the different part of development very clear-cut.

- Reader function is a **GUI-independent** function that reads a file and returns
  a `WidgetDataModel`.

    ``` python title="Example reader function"
    def read_txt(file_path: Path) -> WidgetDataModel:
        text_value = file_path.read_text()
        return WidgetDataModel(value=text_value, type="text")
    ```

    A proper widget class will be automatically selected based on the `type` field, and
    updated based on the returned model using `update_model()` method.

- Writer function is a **GUI-independent** function that writes a `WidgetDataModel`
  to a file.

    ``` python title="Example writer function"
    def write_text(file_path: Path, model: WidgetDataModel):
        file_path.write_text(model.value)
    ```

    A widget will be automatically converted to a model using `to_model()` method before
    calling this writer function.

- Any function for data processing or analysis is also **GUI-independent** functions
  that just convert a `WidgetDataModel` into another.

    ``` python title="Example data processing function"
    def to_upper(model: WidgetDataModel) -> WidgetDataModel:
        assert isinstance(model.value, str)
        return WidgetDataModel(value=model.value.upper(), type="text")
    ```

    A widget will be automatically converted to a model using `to_model()` method before
    calling this function, and sent back to the GUI as another widget created based on the
    returned model.

#### To summarize

Let's say you intend to read a text file, convert it into a table and save it to the
local disk.

![](../images/02_chart_io.png)

- If you are a user, you will not see the "memory" layer. You will open the text file
  (1, 2), run the command to convert it to a table (3, 4, 5), and save the table to the
  local disk (6, 7).
- If you are a plugin developer, you will implement the reader function (1), the text
  editor widget with the proper protocols (2, 3), the converter function (4), the table
  viewer widget with the proper protocols (5, 6), and the writer function (7).

It is interesting to note that what plugin developers do are always half step behind
what users do.

## Choosing the Type

You can use any string for `type` field, but to make your widget interpretable for
the `himena` built-in functions and probably for other plugins, you may want to
use the [`StandardType`][himena.consts.StandardType].

``` python
from himena.const import StandardType

StandardType.TEXT  # "text"
StandardType.TABLE  # "table"
StandardType.ARRAY  # "array"
StandardType.IMAGE  # "array.image"
```

??? info "The list of the pre-defined standards"

    Basic types

    | String type      | Constant                | Internal Python object type             |
    |:----------------:|:-----------------------:|:---------------------------------------:|
    |`"text"`          |`StandardType.TEXT`      | `str`                                   |
    |`"table"`         |`StandardType.TABLE`     | `ndarray` of `np.dtypes.StringDType`    |
    |`"array"`         |`StandardType.ARRAY`     | array-like object of numerical dtype    |
    |`"dataframe"`     |`StandardType.DATAFRAME` | Any dataframe-like object such as `dict[str, ndarray]`, `pandas.DataFrame` and `polars.DataFrame` |
    |`"dict"`          |`StandardType.DICT`      | `dict[str, T]`, where T is any type     |
    |`"plot"`          |`StandardType.PLOT`      | `himena.standard.plotting.BaseLayoutModel` object|
    |`"rois"`          |`StandardType.ROIS`     | `himena.standard.roi.RoiListModel` object|
    |`"matplotlib-figure"`|`StandardType.MPL_FIGURE`| `matplotlib.Figure` object           |
    |`"mesh"`          |`StandardType.MESH`      | tuple of vertices, faces and values     |
    |`"models"`        |`StandardType.MODELS`    | `list[WidgetDataModel]`                 |
    |`"function"`      |`StandardType.FUNCTION`  | any callable object                     |
    |`"lazy"`          |`StandardType.LAZY`      | callable `() -> WidgetDataModel`        |
    |`"workflow"`      |`StandardType.WORKFLOW`  | `himena.workflow.Workflow` object       |

    Subtypes

    |`"array.image"`   |`StandardType.IMAGE`     | array-like object of numerical dtype    |
    |`"array.image.labels"`|`StandardType.IMAGE_LABELS`| array-like object of integer dtype|
    |`"dict.table"`|`StandardType.EXCEL`| `dict[str, ndarray]`, where the dtype of the array is `np.dtypes.StringDType`|

You can use "." to separate the type into a hierarchy. For example, the standard type
`"array.image"` is used for an image data, but it is under "array" type because all the
image data are essentially arrays. A benefit of this subtyping is that all the "array"
functions can be applied to the "array.image" data.

## More Specifications

You can set other fields of `WidgetDataModel` to provide more details of how to convert
the data to a widget.

``` python
WidgetDataModel(
    value="abc",
    type="text",
    title="My Text"  # title of the widget
    extension_default=".txt",  # default file extension in the save dialog
    extensions=[".txt", ".md"]  # allowed file extensions in the save dialog
)
```
