"""Definition of fixtures for static data, sessions etc. used by unit tests."""

from flask import current_app
import pytest

from src.api import *


@pytest.fixture
def client():
    """Provide the client session used by tests."""
    with app.test_client() as client:
        yield client
