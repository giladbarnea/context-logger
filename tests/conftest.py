import pytest


@pytest.fixture(scope="function")
def current_test_name(request):
    return request.node.name.replace("[", "_").replace("]", "_").lower()
