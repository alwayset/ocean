from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Provider(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "providers"

    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    homepage_url: Mapped[str | None] = mapped_column(String(512))
    icon_url: Mapped[str | None] = mapped_column(String(512))

    tools: Mapped[list["Tool"]] = relationship(back_populates="provider")  # noqa: F821
