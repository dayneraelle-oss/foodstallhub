from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all PostgreSQL SQLAlchemy models."""


from app.models import menu, order, stall, user  # noqa: E402, F401