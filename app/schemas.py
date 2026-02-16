from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    telegram_id: int = Field(..., ge=1)


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileResponse(BaseModel):
    character_id: str
    level: int
    hp_current: int
    hp_max: int
    atk: int
    arena_rating: int


class ProgressionResponse(BaseModel):
    level: int
    xp_current: int
    hp_current: int
    hp_max: int
    atk: int


class StartCombatRequest(BaseModel):
    mob_level: int = Field(..., ge=1, le=20)


class CombatStateResponse(BaseModel):
    combat_id: str
    status: Literal["active", "finished"]
    turn_number: int
    current_actor: Literal["player", "enemy"]
    turn_expires_at: datetime
    player_hp: int
    enemy_hp: int
    result: Optional[Literal["win", "lose"]]


class TurnActionRequest(BaseModel):
    zone: Optional[Literal["up", "mid", "down"]] = None
