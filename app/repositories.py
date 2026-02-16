from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from random import choice
from typing import Dict, Literal, Optional
from uuid import uuid4

from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .models import Character as CharacterModel
from .models import Combat as CombatModel
from .models import CombatTurn as CombatTurnModel
from .models import User as UserModel

Zone = Literal["up", "mid", "down"]


@dataclass
class CharacterDTO:
    id: str
    telegram_id: int
    level: int
    xp_current: int
    hp_current: int
    hp_max: int
    atk: int
    arena_rating: int


@dataclass
class CombatDTO:
    id: str
    character_id: str
    status: Literal["active", "finished"]
    turn_number: int
    current_actor: Literal["player", "enemy"]
    turn_expires_at: datetime
    player_hp: int
    enemy_hp: int
    result: Optional[Literal["win", "lose"]]
    player_block_zone: Optional[Zone] = None


class StorageBackend:
    def auth_telegram(self, telegram_id: int) -> str: ...
    def get_character_by_token(self, token: str) -> Optional[CharacterDTO]: ...
    def create_combat(self, character: CharacterDTO, mob_level: int) -> CombatDTO: ...
    def get_combat(self, character_id: str, combat_id: str) -> Optional[CombatDTO]: ...
    def save_combat(self, combat: CombatDTO) -> None: ...
    def add_turn(self, combat: CombatDTO, actor: str, action_type: str, target_zone: Optional[str], resolved_damage: int) -> None: ...


class InMemoryBackend(StorageBackend):
    def __init__(self) -> None:
        self.characters: Dict[str, CharacterDTO] = {}
        self.sessions: Dict[str, str] = {}
        self.combats: Dict[str, CombatDTO] = {}

    def auth_telegram(self, telegram_id: int) -> str:
        char = None
        for c in self.characters.values():
            if c.telegram_id == telegram_id:
                char = c
                break
        if char is None:
            cid = str(uuid4())
            char = CharacterDTO(cid, telegram_id, 1, 0, 100, 100, 1, 1000)
            self.characters[cid] = char
        token = str(uuid4())
        self.sessions[token] = char.id
        return token

    def get_character_by_token(self, token: str) -> Optional[CharacterDTO]:
        cid = self.sessions.get(token)
        return self.characters.get(cid) if cid else None

    def create_combat(self, character: CharacterDTO, mob_level: int) -> CombatDTO:
        for c in self.combats.values():
            if c.character_id == character.id and c.status == "active":
                raise ValueError("Active combat already exists")
        enemy_hp = 80 + 20 * mob_level
        combat = CombatDTO(
            id=f"cmb_{len(self.combats)+1}",
            character_id=character.id,
            status="active",
            turn_number=1,
            current_actor="player",
            turn_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
            player_hp=character.hp_current,
            enemy_hp=enemy_hp,
            result=None,
        )
        self.combats[combat.id] = combat
        return combat

    def get_combat(self, character_id: str, combat_id: str) -> Optional[CombatDTO]:
        c = self.combats.get(combat_id)
        if not c or c.character_id != character_id:
            return None
        return c

    def save_combat(self, combat: CombatDTO) -> None:
        self.combats[combat.id] = combat

    def add_turn(self, combat: CombatDTO, actor: str, action_type: str, target_zone: Optional[str], resolved_damage: int) -> None:
        return


class PostgresBackend(StorageBackend):
    def __init__(self) -> None:
        self.sessions: Dict[str, str] = {}

    @staticmethod
    def _to_character_dto(model: CharacterModel, telegram_id: int) -> CharacterDTO:
        return CharacterDTO(
            id=model.id,
            telegram_id=telegram_id,
            level=model.level,
            xp_current=model.xp_current,
            hp_current=model.hp_current,
            hp_max=model.hp_max,
            atk=model.atk_base,
            arena_rating=model.arena_rating,
        )

    @staticmethod
    def _to_combat_dto(model: CombatModel) -> CombatDTO:
        return CombatDTO(
            id=model.id,
            character_id=model.character_id,
            status=model.status,
            turn_number=model.turn_number,
            current_actor=model.current_actor,
            turn_expires_at=model.turn_expires_at,
            player_hp=model.player_hp,
            enemy_hp=model.enemy_hp,
            result=model.result,
            player_block_zone=model.player_block_zone,
        )

    def auth_telegram(self, telegram_id: int) -> str:
        with SessionLocal() as db:
            user = db.execute(select(UserModel).where(UserModel.telegram_id == telegram_id)).scalar_one_or_none()
            if user is None:
                user = UserModel(id=str(uuid4()), telegram_id=telegram_id)
                db.add(user)
                character = CharacterModel(id=str(uuid4()), user_id=user.id)
                db.add(character)
                db.commit()
                db.refresh(character)
            else:
                character = db.execute(select(CharacterModel).where(CharacterModel.user_id == user.id)).scalar_one()

        token = str(uuid4())
        self.sessions[token] = character.id
        return token

    def get_character_by_token(self, token: str) -> Optional[CharacterDTO]:
        cid = self.sessions.get(token)
        if not cid:
            return None
        with SessionLocal() as db:
            character = db.get(CharacterModel, cid)
            if character is None:
                return None
            user = db.get(UserModel, character.user_id)
            return self._to_character_dto(character, user.telegram_id if user else 0)

    def create_combat(self, character: CharacterDTO, mob_level: int) -> CombatDTO:
        with SessionLocal() as db:
            active = db.execute(
                select(CombatModel).where(CombatModel.character_id == character.id, CombatModel.status == "active")
            ).scalar_one_or_none()
            if active:
                raise ValueError("Active combat already exists")
            combat = CombatModel(
                id=f"cmb_{uuid4()}",
                character_id=character.id,
                mob_name=f"mob_lvl_{mob_level}",
                mode="pve",
                status="active",
                turn_number=1,
                current_actor="player",
                turn_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
                player_hp=character.hp_current,
                enemy_hp=80 + 20 * mob_level,
            )
            db.add(combat)
            db.commit()
            db.refresh(combat)
            return self._to_combat_dto(combat)

    def get_combat(self, character_id: str, combat_id: str) -> Optional[CombatDTO]:
        with SessionLocal() as db:
            combat = db.get(CombatModel, combat_id)
            if not combat or combat.character_id != character_id:
                return None
            return self._to_combat_dto(combat)

    def save_combat(self, combat: CombatDTO) -> None:
        with SessionLocal() as db:
            model = db.get(CombatModel, combat.id)
            if model is None:
                return
            model.status = combat.status
            model.turn_number = combat.turn_number
            model.current_actor = combat.current_actor
            model.turn_expires_at = combat.turn_expires_at
            model.player_hp = combat.player_hp
            model.enemy_hp = combat.enemy_hp
            model.result = combat.result
            model.player_block_zone = combat.player_block_zone
            db.commit()

    def add_turn(self, combat: CombatDTO, actor: str, action_type: str, target_zone: Optional[str], resolved_damage: int) -> None:
        with SessionLocal() as db:
            turn = CombatTurnModel(
                id=str(uuid4()),
                combat_id=combat.id,
                turn_number=combat.turn_number,
                actor_side=actor,
                action_type=action_type,
                target_zone=target_zone,
                resolved_damage=resolved_damage,
            )
            db.add(turn)
            db.commit()


def get_backend() -> StorageBackend:
    if settings.storage_backend.lower() == "postgres":
        return PostgresBackend()
    return InMemoryBackend()


backend = get_backend()


def roll_enemy_zone() -> Zone:
    return choice(["up", "mid", "down"])
