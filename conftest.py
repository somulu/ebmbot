"""Configuration for pytest.
"""

import os

import pytest

from ebmbot import settings

pytest.register_assert_rewrite("tests.assertions")


@pytest.fixture(autouse=True)
def reset_db():
    try:
        os.remove(settings.DB_PATH)
    except FileNotFoundError:
        pass
