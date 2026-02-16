from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException

from .config import settings
from .repositories import CombatDTO, backend, roll_enemy_zone
from .schemas import (
    CombatStateResponse,
    ProfileResponse,
    ProgressionResponse,
    StartCombatRequest,
    TelegramAuthRequest,
    TelegramAuthResponse,
    TurnActionRequest,
)

app = FastAPI(title=settings.app_name, version=settings.app_version)


def _auth(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    char = backend.get_character_by_token(token)
    if not char:
        raise HTTPException(status_code=401, detail="Invalid token")
    return char


def _state(combat: CombatDTO) -> CombatStateResponse:
    return CombatStateResponse(
        combat_id=combat.id,
        status=combat.status,
        turn_number=combat.turn_number,
        current_actor=combat.current_actor,
        turn_expires_at=combat.turn_expires_at,
        player_hp=combat.player_hp,
        enemy_hp=combat.enemy_hp,
        result=combat.result,
    )


def _ensure_turn_timeout(combat: CombatDTO) -> CombatDTO:
    if combat.status != "active":
        return combat
    now = datetime.now(timezone.utc)
    if now <= combat.turn_expires_at:
        return combat
    backend.add_turn(combat, combat.current_actor, "skip", None, 0)
    combat.turn_number += 1
    combat.current_actor = "enemy" if combat.current_actor == "player" else "player"
    combat.turn_expires_at = now + timedelta(seconds=30)
    backend.save_combat(combat)
    return combat


def _resolve_enemy_turn(combat: CombatDTO) -> CombatDTO:
    if combat.status != "active" or combat.current_actor != "enemy":
        return combat

    enemy_zone = roll_enemy_zone()
    raw = 8
    dmg = int(raw * 0.5) if combat.player_block_zone == enemy_zone else raw
    combat.player_hp = max(0, combat.player_hp - dmg)
    backend.add_turn(combat, "enemy", "attack", enemy_zone, dmg)

    if combat.player_hp == 0:
        combat.status = "finished"
        combat.result = "lose"
    else:
        combat.turn_number += 1
        combat.current_actor = "player"
        combat.turn_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)

    combat.player_block_zone = None
    backend.save_combat(combat)
    return combat


@app.get("/health")
def health():
    return {"status": "ok", "backend": settings.storage_backend}


@app.post("/api/v1/auth/telegram", response_model=TelegramAuthResponse)
def auth_telegram(payload: TelegramAuthRequest):
    token = backend.auth_telegram(payload.telegram_id)
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
    try:
        combat = backend.create_combat(character, payload.mob_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _state(combat)


@app.get("/api/v1/combat/{combat_id}/state", response_model=CombatStateResponse)
def combat_state(combat_id: str, character=Depends(_auth)):
    combat = backend.get_combat(character.id, combat_id)
    if combat is None:
        raise HTTPException(status_code=404, detail="Combat not found")
    combat = _ensure_turn_timeout(combat)
    return _state(combat)


@app.post("/api/v1/combat/{combat_id}/turn/attack", response_model=CombatStateResponse)
def combat_attack(combat_id: str, payload: TurnActionRequest, character=Depends(_auth)):
    combat = backend.get_combat(character.id, combat_id)
    if combat is None:
        raise HTTPException(status_code=404, detail="Combat not found")
    combat = _ensure_turn_timeout(combat)
    if combat.status != "active":
        return _state(combat)
    if combat.current_actor != "player":
        raise HTTPException(status_code=409, detail="Not player's turn")
    if payload.zone is None:
        raise HTTPException(status_code=400, detail="zone is required")

    dmg = character.atk
    combat.enemy_hp = max(0, combat.enemy_hp - dmg)
    backend.add_turn(combat, "player", "attack", payload.zone, dmg)

    if combat.enemy_hp == 0:
        combat.status = "finished"
        combat.result = "win"
        backend.save_combat(combat)
        return _state(combat)

    combat.current_actor = "enemy"
    combat.turn_number += 1
    combat.turn_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    backend.save_combat(combat)
    combat = _resolve_enemy_turn(combat)
    return _state(combat)


@app.post("/api/v1/combat/{combat_id}/turn/block", response_model=CombatStateResponse)
def combat_block(combat_id: str, payload: TurnActionRequest, character=Depends(_auth)):
    combat = backend.get_combat(character.id, combat_id)
    if combat is None:
        raise HTTPException(status_code=404, detail="Combat not found")
    combat = _ensure_turn_timeout(combat)
    if combat.status != "active":
        return _state(combat)
    if payload.zone is None:
        raise HTTPException(status_code=400, detail="zone is required")

    combat.player_block_zone = payload.zone
    backend.save_combat(combat)
    return _state(combat)
