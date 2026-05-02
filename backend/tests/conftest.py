import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def client():
    from app import create_app
    app = create_app(testing=True)
    with app.test_client() as c:
        yield c
