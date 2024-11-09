from himena.builtins.qt.output._widget import get_interface


def test_stdout(qtbot):
    interf = get_interface()
    widget = interf.widget
    assert widget.toPlainText() == ""
    print("Hello")
    assert widget.toPlainText() == "Hello\n"
