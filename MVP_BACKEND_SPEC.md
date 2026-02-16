# MVP Backend Spec (Telegram Mini App RPG)

Документ фиксирует минимально-достаточную серверную реализацию для старта разработки.
Опирается на `GAME_DESIGN.md` и `BALANCE_1_20.md`.

## 1) Границы MVP

В MVP входят:
1. Авторизация через Telegram Mini App
2. Профиль персонажа и прогрессия
3. PvE-бой 1vE (3 направления, 30 сек ход, блок 50%)
4. Инвентарь, экипировка, прочность, ремонт
5. Городские действия (тренировка, базовые квесты)
6. Арена с 10 уровня (только рейтинг)
7. Патруль (раз в 6 часов, соло/группа)
8. Друзья и внутриигровая почта

## 2) Архитектура (первый релиз)

- **Client**: Telegram Mini App (Web)
- **API**: REST + JWT session
- **Realtime**: WebSocket для боев и уведомлений
- **DB**: PostgreSQL
- **Cache/Locks**: Redis
- **Workers**: фоновые задачи (реген вне боя, почта, квестовые тики, патруль)

## 3) Доменные сущности (таблицы БД)

Ниже — минимальный набор таблиц для MVP.

### 3.1 Пользователь и персонаж

### `users`
- `id` (uuid, pk)
- `telegram_id` (bigint, unique)
- `username` (text, nullable)
- `created_at`, `updated_at`

### `characters`
- `id` (uuid, pk)
- `user_id` (uuid, fk -> users.id, unique)
- `name` (text)
- `level` (int)
- `xp_current` (int)
- `xp_total` (int)
- `hp_current` (int)
- `hp_max` (int)
- `atk_base` (int)
- `regen_base` (numeric)
- `silver` (int)
- `copper` (int)
- `gold` (int)
- `arena_rating` (int, default 1000)
- `city_id` (uuid, fk)
- `last_free_training_at` (timestamp, nullable)
- `training_buff_until` (timestamp, nullable)
- `training_buff_percent` (int, default 20)
- `created_at`, `updated_at`

### 3.2 Справочники

### `cities`
- `id` (uuid, pk)
- `code` (text, unique)
- `name` (text)

### `item_templates`
- `id` (uuid, pk)
- `code` (text, unique)
- `name` (text)
- `slot` (enum: bracers, shoulders, chest, helmet, legs, boots, weapon_main, weapon_off)
- `rarity` (enum: common, rare, mythic, legendary)
- `tier` (int)
- `hp_bonus` (int)
- `atk_bonus` (int)
- `regen_bonus` (numeric)
- `durability_max` (int)
- `is_tradeable` (bool)

### `mob_templates`
- `id` (uuid, pk)
- `level` (int)
- `name` (text)
- `hp` (int)
- `atk` (int)
- `xp_reward` (int)
- `copper_min` (int)
- `copper_max` (int)

### 3.3 Инвентарь и экипировка

### `character_items`
- `id` (uuid, pk)
- `character_id` (uuid, fk)
- `item_template_id` (uuid, fk)
- `durability_current` (int)
- `durability_max` (int)
- `is_equipped` (bool)
- `equipped_slot` (enum, nullable)
- `acquired_at` (timestamp)

### `inventory_limits`
- `character_id` (uuid, pk/fk)
- `slots_total` (int)
- `slots_used` (int)

### 3.4 Бои

### `combats`
- `id` (uuid, pk)
- `character_id` (uuid, fk)
- `mode` (enum: pve, arena)
- `status` (enum: pending, active, finished, cancelled)
- `started_at`, `finished_at`
- `turn_number` (int)
- `current_actor` (enum: player, enemy)
- `turn_expires_at` (timestamp)
- `result` (enum: win, lose, draw, nullable)

### `combat_participants`
- `id` (uuid, pk)
- `combat_id` (uuid, fk)
- `side` (enum: player, enemy)
- `entity_type` (enum: character, mob, arena_character)
- `entity_ref_id` (uuid)
- `hp_current` (int)
- `hp_max` (int)
- `atk_effective` (int)

### `combat_turns`
- `id` (uuid, pk)
- `combat_id` (uuid, fk)
- `turn_number` (int)
- `actor_side` (enum)
- `action_type` (enum: attack, block, skip, super)
- `target_zone` (enum: up, mid, down, nullable)
- `resolved_damage` (int)
- `created_at` (timestamp)

### 3.5 Квесты

### `quest_templates`
- `id` (uuid, pk)
- `code` (text, unique)
- `type` (enum: daily_short, daily_medium, factional, story)
- `objective_type` (enum: kill_mob, close_portal, patrol, arena)
- `objective_value` (int)
- `xp_reward` (int)
- `copper_reward` (int)
- `silver_reward` (int)

### `character_quests`
- `id` (uuid, pk)
- `character_id` (uuid, fk)
- `quest_template_id` (uuid, fk)
- `progress` (int)
- `status` (enum: active, completed, claimed, failed)
- `accepted_at`, `expires_at`

### 3.6 Социальные системы

### `friends`
- `id` (uuid, pk)
- `requester_character_id` (uuid, fk)
- `addressee_character_id` (uuid, fk)
- `status` (enum: pending, accepted, rejected, blocked)
- `created_at`, `updated_at`

### `mail_messages`
- `id` (uuid, pk)
- `from_character_id` (uuid, fk)
- `to_character_id` (uuid, fk)
- `subject` (text)
- `body` (text)
- `is_read` (bool)
- `created_at`, `read_at`

### 3.7 Торговля

### `market_listings`
- `id` (uuid, pk)
- `seller_character_id` (uuid, fk)
- `character_item_id` (uuid, fk)
- `price_copper` (int)
- `status` (enum: active, sold, cancelled)
- `created_at`, `sold_at`

### `market_transactions`
- `id` (uuid, pk)
- `listing_id` (uuid, fk)
- `buyer_character_id` (uuid, fk)
- `gross_price_copper` (int)
- `fee_copper` (int)   -- 2%
- `net_to_seller_copper` (int)
- `created_at`

## 4) Основные формулы (server-authoritative)

1. **Блок**: если зона блока совпала с зоной атаки ->
   `damage_final = floor(damage_raw * 0.5)`

2. **Таймаут хода**: если `now > turn_expires_at` и ход не зафиксирован ->
   создать `combat_turn(action_type=skip)` и передать ход второй стороне.

3. **Тренировка** (1 час):
   - `hp_max_effective = floor(hp_max * 1.2)`
   - `atk_effective = floor(atk_effective * 1.2)`
   - `regen_effective = regen_base * 1.2`

4. **Торговая комиссия**:
   - `fee_copper = floor(gross_price_copper * 0.02)`
   - `net_to_seller = gross - fee`

5. **Смерть**:
   - выбрать 1 случайный экипированный предмет
   - `durability_current = max(0, durability_current - 1)`
   - при `0` прочности предмет удаляется

## 5) API контракты (черновик)

## 5.1 Auth / Profile
- `POST /api/v1/auth/telegram` — логин по initData, возвращает JWT
- `GET /api/v1/profile/me` — профиль персонажа
- `GET /api/v1/profile/progression` — level/xp/hp/atk

## 5.2 City / Training / Quests
- `POST /api/v1/city/training/free` — бесплатная тренировка (1/сутки)
- `POST /api/v1/city/training/paid` — платная тренировка (2 серебра)
- `GET /api/v1/quests` — активные/доступные квесты
- `POST /api/v1/quests/{questId}/accept`
- `POST /api/v1/quests/{questId}/claim`

## 5.3 Inventory / Equipment / Repair
- `GET /api/v1/inventory`
- `POST /api/v1/inventory/equip`
- `POST /api/v1/inventory/unequip`
- `POST /api/v1/blacksmith/repair` — ремонт предмета

## 5.4 PvE Combat
- `POST /api/v1/combat/pve/start` — старт боя с мобом
- `POST /api/v1/combat/{combatId}/turn/attack` — выбрать зону атаки
- `POST /api/v1/combat/{combatId}/turn/block` — выбрать зону блока
- `POST /api/v1/combat/{combatId}/turn/super` — суперудар
- `GET /api/v1/combat/{combatId}/state`

## 5.5 Arena (unlock lvl10)
- `POST /api/v1/arena/matchmaking/join`
- `POST /api/v1/arena/matchmaking/leave`
- `GET /api/v1/arena/leaderboard`

Сервер валидирует `character.level >= 10`.

## 5.6 Patrol
- `POST /api/v1/patrol/start` (zone, partyId?)
- `GET /api/v1/patrol/{patrolId}/state`
- `POST /api/v1/patrol/{patrolId}/finish`

Сервер валидирует КД 6 часов.

## 5.7 Social
- `POST /api/v1/friends/request`
- `POST /api/v1/friends/{friendshipId}/accept`
- `GET /api/v1/friends`
- `POST /api/v1/mail/send`
- `GET /api/v1/mail/inbox`
- `POST /api/v1/mail/{messageId}/read`

## 6) WebSocket события

Каналы:
- `combat:{combatId}`
- `notifications:{characterId}`
- `chat:city:{cityId}`

События:
- `combat.turn_started`
- `combat.turn_resolved`
- `combat.finished`
- `mail.new`
- `friend.requested`
- `chat.message`

## 7) Минимальные проверки/ограничения

1. Все валютные операции в integer (медяки) на сервере.
2. Нельзя инициировать второй активный бой при незавершенном первом.
3. Все вычисления урона/дропа/XP только на сервере.
4. Лимит рейтинговых арен: 10/сутки.
5. Переход между городами автоматически переключает чат-канал.

## 8) План реализации (технический)

### Фаза A — Core backend (1–1.5 недели)
- auth, profile, character progression
- PvE combat state machine + turn timer (30s)
- inventory/equipment basics

### Фаза B — Economy + city (1 неделя)
- training free/paid
- repair/durability
- quests v1

### Фаза C — Social + arena + patrol (1–1.5 недели)
- friends + mail + city chat
- arena matchmaking + leaderboard
- patrol loop + cooldown

## 9) Критерии готовности MVP

1. Новый игрок может: зарегистрироваться, провести 3–5 PvE боев, получить лут, надеть предмет, починить его.
2. Игрок 10 уровня может: зайти на арену и увидеть изменение рейтинга.
3. Игрок может: добавить друга, отправить письмо и получить индикатор нового сообщения.
4. Нет client-side доверия для боевой математики и валют.
