from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(512))
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    filesize: Mapped[Optional[int]] = mapped_column(BigInteger)
    language: Mapped[Optional[str]] = mapped_column(String(20))
    md5: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    year: Mapped[Optional[str]] = mapped_column(String(10))
    publisher: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_books_extension", "extension"),
        Index("idx_books_language", "language"),
    )
