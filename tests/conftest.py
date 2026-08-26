"""Pytest configuration and test setup."""

import pytest
import os

# Set testing environment variable
os.environ["APP_ENV"] = "testing"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:TEST_BOT_TOKEN_FOR_PYTEST_MOCK"
