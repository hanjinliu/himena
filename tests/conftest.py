import tempfile
import pytest

@pytest.fixture(scope="session", autouse=True)
def patch_user_data_dir(request: pytest.FixtureRequest):
    from royalapp.profile import patch_user_data_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch_user_data_dir(tmpdir):
            yield
