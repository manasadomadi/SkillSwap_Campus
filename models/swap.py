from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship

from datetime import datetime

from services.database import Base


class SwapRequest(Base):
    __tablename__ = "swap_requests"

    id = Column(Integer, primary_key=True)

    sender_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    receiver_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    skill_offered = Column(
        String(100),
        nullable=False
    )

    skill_requested = Column(
        String(100),
        nullable=False
    )

    message = Column(
        Text,
        default=""
    )

    status = Column(
        String(30),
        default="Pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    sender = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_requests"
    )

    receiver = relationship(
        "User",
        foreign_keys=[receiver_id],
        back_populates="received_requests"
    )