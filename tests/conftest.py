import pytest

@pytest.fixture(scope="function", params=["mock", "qt"])
def backend(request: pytest.FixtureRequest):
    yield request.param
