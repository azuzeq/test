from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional
from uuid import uuid4

Zone = Literal["up", "mid", "down"]
ActionType = Literal["attack", "block", "skip", "super"]


@dataclass
class Character:
    id: str
    telegram_id: int
    level: int = 1
    xp_current: int = 0
    hp_max: int = 100
    hp_current: int = 100
    atk: int = 1
    arena_rating: int = 1000


@dataclass
class CombatTurn:
    turn_number: int
    actor: Literal["player", "enemy"]
    action_type: ActionType
    target_zone: Optional[Zone]
    resolved_damage: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Combat:
    id: str
    character_id: str
    mob_name: str
    status: Literal["active", "finished"] = "active"
    turn_number: int = 1
    current_actor: Literal["player", "enemy"] = "player"
    turn_expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=30))
    result: Optional[Literal["win", "lose"]] = None
    player_hp: int = 0
    enemy_hp: int = 0
    player_block_zone: Optional[Zone] = None
    turns: List[CombatTurn] = field(default_factory=list)


class InMemoryStore:
    def __init__(self) -> None:
        self.characters: Dict[str, Character] = {}
        self.sessions: Dict[str, str] = {}
        self.combats: Dict[str, Combat] = {}

    def upsert_character(self, telegram_id: int) -> Character:
        for c in self.characters.values():
            if c.telegram_id == telegram_id:
                return c
        cid = str(uuid4())
        char = Character(id=cid, telegram_id=telegram_id)
        self.characters[cid] = char
        return char

    def create_session(self, character_id: str) -> str:
        token = str(uuid4())
        self.sessions[token] = character_id
        return token

    def get_character_by_token(self, token: str) -> Optional[Character]:
        cid = self.sessions.get(token)
        return self.characters.get(cid) if cid else None


store = InMemoryStore()
