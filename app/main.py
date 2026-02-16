from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import choice
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException

from .schemas import (
    CombatStateResponse,
    ProfileResponse,
    ProgressionResponse,
    StartCombatRequest,
    TelegramAuthRequest,
    TelegramAuthResponse,
    TurnActionRequest,
)
from .store import Combat, CombatTurn, store

app = FastAPI(title="Telegram RPG MVP API", version="0.1.0")


def _mob_stats(level: int) -> tuple[str, int, int]:
    hp = 80 + 20 * level
    atk = 8 + 2 * level
    return (f"mob_lvl_{level}", hp, atk)


def _auth(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    char = store.get_character_by_token(token)
    if not char:
        raise HTTPException(status_code=401, detail="Invalid token")
    return char


def _ensure_turn_timeout(combat: Combat) -> None:
    if combat.status != "active":
        return
    now = datetime.now(timezone.utc)
    if now <= combat.turn_expires_at:
        return
    combat.turns.append(
        CombatTurn(
            turn_number=combat.turn_number,
            actor=combat.current_actor,
            action_type="skip",
            target_zone=None,
            resolved_damage=0,
        )
    )
    combat.turn_number += 1
    combat.current_actor = "enemy" if combat.current_actor == "player" else "player"
    combat.turn_expires_at = now + timedelta(seconds=30)


def _resolve_enemy_turn(combat: Combat, player_block_zone: Literal["up", "mid", "down"] | None) -> None:
    if combat.status != "active" or combat.current_actor != "enemy":
        return
    enemy_zone = choice(["up", "mid", "down"])
    raw = 8
    dmg = int(raw * 0.5) if player_block_zone == enemy_zone else raw
    combat.player_hp = max(0, combat.player_hp - dmg)
    combat.turns.append(
        CombatTurn(
            turn_number=combat.turn_number,
            actor="enemy",
            action_type="attack",
            target_zone=enemy_zone,
            resolved_damage=dmg,
        )
    )
    if combat.player_hp == 0:
        combat.status = "finished"
        combat.result = "lose"
        return
    combat.turn_number += 1
    combat.current_actor = "player"
    combat.turn_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/auth/telegram", response_model=TelegramAuthResponse)
def auth_telegram(payload: TelegramAuthRequest):
    character = store.upsert_character(payload.telegram_id)
    token = store.create_session(character.id)
    return TelegramAuthResponse(access_token=token)


@app.get("/api/v1/profile/me", response_model=ProfileResponse)
def profile_me(character=Depends(_auth)):
    return ProfileResponse(
        character_id=character.id,
        level=character.level,
        hp_current=character.hp_current,
        hp_max=character.hp_max,
        atk=character.atk,
        arena_rating=character.arena_rating,
    )


@app.get("/api/v1/profile/progression", response_model=ProgressionResponse)
def progression(character=Depends(_auth)):
    return ProgressionResponse(
        level=character.level,
        xp_current=character.xp_current,
        hp_current=character.hp_current,
        hp_max=character.hp_max,
        atk=character.atk,
    )


@app.post("/api/v1/combat/pve/start", response_model=CombatStateResponse)
def combat_start(payload: StartCombatRequest, character=Depends(_auth)):
    for c in store.combats.values():
        if c.character_id == character.id and c.status == "active":
            raise HTTPException(status_code=400, detail="Active combat already exists")

    mob_name, mob_hp, _ = _mob_stats(payload.mob_level)
    combat = Combat(
        id=f"cmb_{len(store.combats)+1}",
        character_id=character.id,
        mob_name=mob_name,
        player_hp=character.hp_current,
        enemy_hp=mob_hp,
    )
    store.combats[combat.id] = combat
    return CombatStateResponse(**combat.__dict__)


@app.get("/api/v1/combat/{combat_id}/state", response_model=CombatStateResponse)
def combat_state(combat_id: str, character=Depends(_auth)):
    combat = store.combats.get(combat_id)
    if not combat or combat.character_id != character.id:
        raise HTTPException(status_code=404, detail="Combat not found")
    _ensure_turn_timeout(combat)
    return CombatStateResponse(**combat.__dict__)


@app.post("/api/v1/combat/{combat_id}/turn/attack", response_model=CombatStateResponse)
def combat_attack(combat_id: str, payload: TurnActionRequest, character=Depends(_auth)):
    combat = store.combats.get(combat_id)
    if not combat or combat.character_id != character.id:
        raise HTTPException(status_code=404, detail="Combat not found")
    _ensure_turn_timeout(combat)
    if combat.status != "active":
        return CombatStateResponse(**combat.__dict__)
    if combat.current_actor != "player":
        raise HTTPException(status_code=409, detail="Not player's turn")
    if payload.zone is None:
        raise HTTPException(status_code=400, detail="zone is required")

    dmg = character.atk
    combat.enemy_hp = max(0, combat.enemy_hp - dmg)
    combat.turns.append(
        CombatTurn(
            turn_number=combat.turn_number,
            actor="player",
            action_type="attack",
            target_zone=payload.zone,
            resolved_damage=dmg,
        )
    )
    if combat.enemy_hp == 0:
        combat.status = "finished"
        combat.result = "win"
        return CombatStateResponse(**combat.__dict__)

    combat.current_actor = "enemy"
    combat.turn_number += 1
    combat.turn_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    _resolve_enemy_turn(combat, combat.player_block_zone)
    combat.player_block_zone = None
    return CombatStateResponse(**combat.__dict__)


@app.post("/api/v1/combat/{combat_id}/turn/block", response_model=CombatStateResponse)
def combat_block(combat_id: str, payload: TurnActionRequest, character=Depends(_auth)):
    combat = store.combats.get(combat_id)
    if not combat or combat.character_id != character.id:
        raise HTTPException(status_code=404, detail="Combat not found")
    _ensure_turn_timeout(combat)
    if combat.status != "active":
        return CombatStateResponse(**combat.__dict__)
    if payload.zone is None:
        raise HTTPException(status_code=400, detail="zone is required")

    combat.player_block_zone = payload.zone
    return CombatStateResponse(**combat.__dict__)
