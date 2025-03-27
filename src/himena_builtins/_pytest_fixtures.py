# pragma: no cover
import tempfile
import warnings
import pytest
import gc
from pathlib import Path
from qtpy.QtWidgets import QApplication
from app_model import Application
from pytestqt.qtbot import QtBot


@pytest.fixture(scope="session", autouse=True)
def patch_user_data_dir(request: pytest.FixtureRequest):
    from himena.profile import patch_user_data_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch_user_data_dir(tmpdir):
            yield


@pytest.fixture
def himena_ui(qtbot: QtBot, request: pytest.FixtureRequest):
    _factory = _make_himena_ui(qtbot, request)
    window = next(_factory)()
    yield window


@pytest.fixture
def make_himena_ui(qtbot: QtBot, request: pytest.FixtureRequest):
    yield from _make_himena_ui(qtbot, request)


def _make_himena_ui(qtbot: QtBot, request: pytest.FixtureRequest):
    from himena import new_window, MainWindow
    from himena._app_model._application import HimenaApplication
    from himena.widgets._initialize import _APP_INSTANCES, cleanup

    if _APP_INSTANCES:
        existing = []
        for ins in _APP_INSTANCES.values():
            for each in ins:
                pytest_name = getattr(each, "_pytest_name", "None")
                existing.append(f"{each} ({pytest_name})")
        existing_str = "    \n".join(existing)
        cleanup()
        warnings.warn(
            f"Instances not cleaned up in the previous session.\n"
            f"Existing instances:\n    {existing_str}",
            RuntimeWarning,
            stacklevel=2,
        )
    window: MainWindow | None = None

    def _factory(backend="qt"):
        nonlocal window
        window = new_window(backend=backend)
        window._instructions = window._instructions.updated(
            confirm=False,
            file_dialog_response=_raise_dialog_error,
            choose_one_dialog_response=_raise_dialog_error,
        )
        window._pytest_name = request.node.name
        if backend == "qt":
            qtbot.add_widget(window._backend_main_window)
        return window

    try:
        yield _factory
    finally:
        assert window is not None
        Application.destroy(window.model_app)
        Application.destroy(".")
        window.close()
        assert window.model_app not in Application._instances
        assert window.model_app not in HimenaApplication._instances
        assert len(_APP_INSTANCES) == 0

        QApplication.processEvents()
        QApplication.processEvents()
        QApplication.processEvents()
        gc.collect()


@pytest.fixture
def sample_dir() -> Path:
    return Path(__file__).parent.parent.parent / "tests" / "samples"


class UserResponseRequested(RuntimeError):
    """Raised when a user response is requested during testing."""


def _raise_dialog_error():  # pragma: no cover
    raise UserResponseRequested(
        "User response is requested during testing. This error is raised to prevent "
        "blocking the test execution. To fix this, you can use the testing functions "
        "`file_dialog_response` and `choose_one_dialog_response` from the "
        "`himena.testing` submodule."
    )
