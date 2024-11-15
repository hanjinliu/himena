import tempfile
import pytest
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
def ui(qtbot: QtBot):
    from himena import new_window

    app = "test-app"
    window = new_window(app=app)
    window._instructions = window._instructions.updated(confirm=False)
    qtbot.add_widget(window._backend_main_window)
    try:
        yield window
    finally:
        Application.destroy(app)
        window.close()
        assert app not in Application._instances

        QApplication.processEvents()
        QApplication.processEvents()
        QApplication.processEvents()

@pytest.fixture
def sample_dir() -> Path:
    return Path(__file__).parent / "samples"
