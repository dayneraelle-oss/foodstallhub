from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.stall import Stall


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stall_id: Mapped[int] = mapped_column(
        ForeignKey("stalls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prep_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    serving_size: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    stall: Mapped["Stall"] = relationship(back_populates="menus")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MenuItem id={self.id} name={self.name} price={self.price}>"