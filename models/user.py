import hashlib
import hmac
import secrets

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from services.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(String(300), nullable=False)

    college = Column(String(150), default="")
    course = Column(String(150), default="")
    year = Column(String(50), default="")

    bio = Column(Text, default="")

    skills = relationship(
        "UserSkill",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    sent_requests = relationship(
        "SwapRequest",
        foreign_keys="SwapRequest.sender_id",
        back_populates="sender"
    )

    received_requests = relationship(
        "SwapRequest",
        foreign_keys="SwapRequest.receiver_id",
        back_populates="receiver"
    )

    # FIXED MESSAGE RELATIONSHIPS
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender"
    )

    received_messages = relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        back_populates="receiver"
    )

    reviews_given = relationship(
        "Review",
        foreign_keys="Review.reviewer_id",
        back_populates="reviewer"
    )

    reviews_received = relationship(
        "Review",
        foreign_keys="Review.reviewed_user_id",
        back_populates="reviewed_user"
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        300000
    )

    return f"{salt.hex()}${password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$")

        salt = bytes.fromhex(salt_hex)

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            300000
        )

        return hmac.compare_digest(
            new_hash.hex(),
            hash_hex
        )

    except Exception:
        return False