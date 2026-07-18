"""Test settings: run the suite against a disposable in-memory SQLite DB.

Keeps `manage.py test` from creating/dropping a test database on the remote
Postgres configured in ``settings.py``. The domain models use no
Postgres-specific fields, so SQLite is a faithful target for the ORM-level and
API contract tests in this project.
"""

from ufc_fantasy.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
