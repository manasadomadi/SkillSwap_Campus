from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey
)

from sqlalchemy.orm import relationship

from services.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)

    name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    category = Column(
        String(100),
        default="Other"
    )

    users = relationship(
        "UserSkill",
        back_populates="skill",
        cascade="all, delete-orphan"
    )


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    skill_id = Column(
        Integer,
        ForeignKey("skills.id"),
        nullable=False
    )

    skill_type = Column(
        String(20),
        nullable=False
    )
    # TEACH or LEARN

    user = relationship(
        "User",
        back_populates="skills"
    )

    skill = relationship(
        "Skill",
        back_populates="users"
    )