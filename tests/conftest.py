"""Pytest configuration and fixtures for libra tests."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set environment variables for testing."""
    # Use a temporary directory for test data
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["LIBRA_DATA_DIR"] = tmpdir
        yield


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
