import os
import tempfile

import pytest

from app import app as flask_app
import database.db as db_module
from database.db import init_db


@pytest.fixture
def app(monkeypatch):
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        init_db()
    yield flask_app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()
