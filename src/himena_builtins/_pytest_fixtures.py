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
    from himena import new_window
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
    window = new_window()
    app = window.model_app
    window._instructions = window._instructions.updated(confirm=False)
    window._pytest_name = request.node.name
    qtbot.add_widget(window._backend_main_window)
    try:
        yield window
    finally:
        Application.destroy(app)
        window.close()
        assert app not in Application._instances
        assert app not in HimenaApplication._instances
        assert len(_APP_INSTANCES) == 0

        QApplication.processEvents()
        QApplication.processEvents()
        QApplication.processEvents()
        gc.collect()


@pytest.fixture
def sample_dir() -> Path:
    return Path(__file__).parent.parent.parent / "tests" / "samples"
