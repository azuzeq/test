-- Initial PostgreSQL schema for MVP Phase A/B foundation

CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(36) PRIMARY KEY,
  telegram_id BIGINT NOT NULL UNIQUE,
  username VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS characters (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id),
  level INT NOT NULL DEFAULT 1,
  xp_current INT NOT NULL DEFAULT 0,
  hp_current INT NOT NULL DEFAULT 100,
  hp_max INT NOT NULL DEFAULT 100,
  atk_base INT NOT NULL DEFAULT 1,
  arena_rating INT NOT NULL DEFAULT 1000,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS combats (
  id VARCHAR(36) PRIMARY KEY,
  character_id VARCHAR(36) NOT NULL REFERENCES characters(id),
  mob_name VARCHAR(64) NOT NULL DEFAULT 'mob_lvl_1',
  mode VARCHAR(16) NOT NULL,
  status VARCHAR(16) NOT NULL,
  turn_number INT NOT NULL DEFAULT 1,
  current_actor VARCHAR(16) NOT NULL DEFAULT 'player',
  player_hp INT NOT NULL DEFAULT 100,
  enemy_hp INT NOT NULL DEFAULT 100,
  turn_expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  player_block_zone VARCHAR(8),
  result VARCHAR(16),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS combat_turns (
  id VARCHAR(36) PRIMARY KEY,
  combat_id VARCHAR(36) NOT NULL REFERENCES combats(id),
  turn_number INT NOT NULL,
  actor_side VARCHAR(16) NOT NULL,
  action_type VARCHAR(16) NOT NULL,
  target_zone VARCHAR(8),
  resolved_damage INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mail_messages (
  id VARCHAR(36) PRIMARY KEY,
  from_character_id VARCHAR(36) NOT NULL,
  to_character_id VARCHAR(36) NOT NULL,
  subject VARCHAR(120) NOT NULL,
  body TEXT NOT NULL,
  is_read INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
