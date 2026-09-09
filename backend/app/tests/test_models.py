from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.menu import MenuItem
from app.models.stall import Stall
from app.models.user import User


def _make_session():
    engine = create_engine("sqlite://")  # in-memory
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_user_stall_menu_relationship_cascade():
    session = _make_session()
    try:
        vendor = User(
            email="vendor@example.com",
            full_name="Vendor One",
            hashed_password="x",
            role="vendor",
        )
        session.add(vendor)
        session.commit()

        stall = Stall(
            owner_id=vendor.id,
            name="Tandoori Junction",
            address="MG Road",
            city="Bengaluru",
            cuisine="indian",
        )
        session.add(stall)
        session.commit()

        item = MenuItem(
            stall_id=stall.id,
            name="Paneer Tikka",
            price=249,
            category="starter",
        )
        session.add(item)
        session.commit()

        assert vendor.stalls[0].id == stall.id
        assert stall.owner.email == "vendor@example.com"
        assert stall.menus[0].name == "Paneer Tikka"

        # Deleting the vendor cascades to stalls and menu items.
        session.delete(vendor)
        session.commit()
        assert session.query(Stall).count() == 0
        assert session.query(MenuItem).count() == 0
    finally:
        session.close()


def test_user_email_unique_enforced():
    session = _make_session()
    try:
        session.add(User(email="a@example.com", full_name="A", hashed_password="x"))
        session.add(User(email="a@example.com", full_name="B", hashed_password="y"))
        import pytest

        with pytest.raises(Exception):
            session.commit()
    finally:
        session.close()