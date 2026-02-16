from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    character: Mapped["Character"] = relationship(back_populates="user", uselist=False)


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp_current: Mapped[int] = mapped_column(Integer, default=0)
    hp_current: Mapped[int] = mapped_column(Integer, default=100)
    hp_max: Mapped[int] = mapped_column(Integer, default=100)
    atk_base: Mapped[int] = mapped_column(Integer, default=1)
    arena_rating: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="character")


class Combat(Base):
    __tablename__ = "combats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    character_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id"), index=True)
    mob_name: Mapped[str] = mapped_column(String(64), default="mob_lvl_1")
    mode: Mapped[str] = mapped_column(String(16), default="pve")
    status: Mapped[str] = mapped_column(String(16), default="active")
    turn_number: Mapped[int] = mapped_column(Integer, default=1)
    current_actor: Mapped[str] = mapped_column(String(16), default="player")
    player_hp: Mapped[int] = mapped_column(Integer, default=100)
    enemy_hp: Mapped[int] = mapped_column(Integer, default=100)
    turn_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    player_block_zone: Mapped[str | None] = mapped_column(String(8), nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CombatTurn(Base):
    __tablename__ = "combat_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    combat_id: Mapped[str] = mapped_column(String(36), ForeignKey("combats.id"), index=True)
    turn_number: Mapped[int] = mapped_column(Integer)
    actor_side: Mapped[str] = mapped_column(String(16))
    action_type: Mapped[str] = mapped_column(String(16))
    target_zone: Mapped[str | None] = mapped_column(String(8), nullable=True)
    resolved_damage: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MailMessage(Base):
    __tablename__ = "mail_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    from_character_id: Mapped[str] = mapped_column(String(36), index=True)
    to_character_id: Mapped[str] = mapped_column(String(36), index=True)
    subject: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
