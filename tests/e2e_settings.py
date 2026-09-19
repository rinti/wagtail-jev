"""Settings for tests/manual_e2e.py: real DB file, API key from environment."""
import os

from tests.settings import *  # noqa: F401,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "tests/test.db"}}
WAGTAIL_JEV_API_KEY = os.environ.get("WAGTAIL_JEV_API_KEY")
