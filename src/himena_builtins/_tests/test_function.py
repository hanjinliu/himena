from functools import partial
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena.consts import StandardType
from himena.testing import WidgetTester
from himena_builtins.qt.widgets import QFunctionEdit

_lambda_function = lambda x: x + 1  # noqa: E731

def _function(x, a, b):
    return x + a - b

class FunctionClass:
    def __init__(self, p):
        self.p = p

    def __call__(self, x, y):
        return x * self.p + y

def test_function_widget(qtbot: QtBot):
    with WidgetTester(QFunctionEdit()) as tester:
        qtbot.addWidget(tester.widget)
        tester.update_model(value=_function)
        tester.cycle_model()
        assert tester.to_model().value is _function

        tester.update_model(value=_lambda_function)
        tester.cycle_model()
        assert tester.to_model().value is _lambda_function

        fn = FunctionClass(-1)
        tester.update_model(value=fn)
        tester.cycle_model()
        assert tester.to_model().value is fn

def test_partial_function_widget(qtbot: QtBot):
    with WidgetTester(QFunctionEdit()) as tester:
        qtbot.addWidget(tester.widget)
        tester.update_model(value=partial(_function, 2, b=2))
        tester.cycle_model()
        assert tester.to_model().value.func is _function

def test_partialize(himena_ui: MainWindow):
    himena_ui.add_object(lambda a, b: a + b, type=StandardType.FUNCTION)
    himena_ui.exec_action("builtins:partialize-function", with_params={"b": "2"})
    assert himena_ui.current_model.value(1) == 3
