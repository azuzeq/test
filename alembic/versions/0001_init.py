"""init schema

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "characters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("xp_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hp_current", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("hp_max", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("atk_base", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("arena_rating", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_characters_user_id", "characters", ["user_id"], unique=True)

    op.create_table(
        "combats",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("character_id", sa.String(length=36), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("mob_name", sa.String(length=64), nullable=False, server_default="mob_lvl_1"),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="pve"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("turn_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_actor", sa.String(length=16), nullable=False, server_default="player"),
        sa.Column("player_hp", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enemy_hp", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("turn_expires_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("player_block_zone", sa.String(length=8), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_combats_character_id", "combats", ["character_id"], unique=False)

    op.create_table(
        "combat_turns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("combat_id", sa.String(length=36), sa.ForeignKey("combats.id"), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("actor_side", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=16), nullable=False),
        sa.Column("target_zone", sa.String(length=8), nullable=True),
        sa.Column("resolved_damage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_combat_turns_combat_id", "combat_turns", ["combat_id"], unique=False)

    op.create_table(
        "mail_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("from_character_id", sa.String(length=36), nullable=False),
        sa.Column("to_character_id", sa.String(length=36), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mail_messages")
    op.drop_index("ix_combat_turns_combat_id", table_name="combat_turns")
    op.drop_table("combat_turns")
    op.drop_index("ix_combats_character_id", table_name="combats")
    op.drop_table("combats")
    op.drop_index("ix_characters_user_id", table_name="characters")
    op.drop_table("characters")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
