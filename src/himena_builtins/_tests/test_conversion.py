import numpy as np
from numpy.testing import assert_array_equal
from himena import MainWindow, StandardType

def test_convert(himena_ui: MainWindow):
    win = himena_ui.add_object("a,b,c\n1,2,3", type=StandardType.TEXT)
    himena_ui.exec_action("builtins:text-to-table")
    assert himena_ui.current_model.type == StandardType.TABLE
    assert himena_ui.current_model.value.tolist() == [["a", "b", "c"], ["1", "2", "3"]]
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:text-to-dataframe")
    assert himena_ui.current_model.type == StandardType.DATAFRAME

    win = himena_ui.add_object("-1,3,4.3\n1.2,2,3", type=StandardType.TEXT)
    himena_ui.exec_action("builtins:text-to-array")
    assert_array_equal(himena_ui.current_model.value, np.array([[-1, 3, 4.3], [1.2, 2, 3]]))

    win = himena_ui.add_object("<b>a</b><br>3", type=StandardType.HTML)
    himena_ui.exec_action("builtins:to-plain-text")
    # FIXME: return value of toHtml() contains "\n". How to process them?
    # assert himena_ui.current_model.type == StandardType.TEXT
    # assert himena_ui.current_model.value == "a\n3"

    win = himena_ui.add_object(
        {"a": [1, 2], "value": ["p", "q"]}, type=StandardType.DATAFRAME,
    )
    himena_ui.exec_action("builtins:dataframe-to-table")
    assert himena_ui.current_model.type == StandardType.TABLE
    assert himena_ui.current_model.value.tolist() == [["a", "value"], ["1", "p"], ["2", "q"]]

    win = himena_ui.add_object({"a": [1, 2], "bbb": ["p", "q"]}, type=StandardType.DATAFRAME)
    himena_ui.exec_action("builtins:dataframe-to-text", with_params={"format": "CSV"})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe-to-text", with_params={"format": "TSV"})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe-to-text", with_params={"format": "Markdown"})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe-to-text", with_params={"format": "Latex"})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe-to-text", with_params={"format": "rST"})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe-to-text", with_params={"format": "HTML"})

    himena_ui.add_object([["xx", "yyy"], [False, -0.33], [True, 2.3]], type=StandardType.TABLE)
    himena_ui.exec_action("builtins:table-to-dataframe")
    himena_ui.add_object([[1, 2], [-1, 2], [3, 2]], type=StandardType.TABLE)
    himena_ui.exec_action("builtins:table-to-array")

    himena_ui.add_object({"x": [4, 3], "y": [3.1, 2.3]}, type=StandardType.DATAFRAME)
    himena_ui.exec_action("builtins:dataframe-to-image-rois", with_params={"roi_type": "point"})
    himena_ui.add_object({"x": [4, 3], "y": [3.1, 2.3], "width": [2, 3], "height": [5, 6]}, type=StandardType.DATAFRAME)
    himena_ui.exec_action("builtins:dataframe-to-image-rois", with_params={"roi_type": "rectangle"})
    himena_ui.add_object({"x": [1, 2, 3], "y": [5, 3, 4]}, type=StandardType.DATAFRAME)
    himena_ui.exec_action("builtins:dataframe-to-dataframe-plot")
    himena_ui.add_object(np.arange(6).reshape(2, 3), type=StandardType.ARRAY)
    himena_ui.exec_action("builtins:array-to-table")
