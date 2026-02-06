from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GatewayHealth(Base):
    __tablename__ = "gateway_health"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    gateway_url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    available: Mapped[bool] = mapped_column(Boolean, default=False)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
