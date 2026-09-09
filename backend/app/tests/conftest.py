"""Pytest bootstrap: keep cwd-independent and make tests DB-free."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-0123456789abc")
os.environ.setdefault("POSTGRES_DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "foodstallhub_test")