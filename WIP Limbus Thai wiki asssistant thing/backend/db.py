from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS import_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  kind TEXT NOT NULL,
  records INTEGER NOT NULL DEFAULT 0,
  details_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identities (
  identity_id TEXT PRIMARY KEY,
  english_name TEXT NOT NULL,
  localized_name TEXT,
  sinner TEXT,
  rarity INTEGER,
  hp INTEGER,
  defense_level INTEGER,
  slash_resistance REAL,
  pierce_resistance REAL,
  blunt_resistance REAL,
  speed_by_uptie_json TEXT,
  stagger_thresholds_json TEXT,
  panic_text TEXT,
  sanity_json TEXT,
  en_json TEXT NOT NULL,
  th_json TEXT,
  combat_json TEXT
);

CREATE TABLE IF NOT EXISTS identity_search_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identity_id TEXT NOT NULL REFERENCES identities(identity_id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  normalized TEXT NOT NULL,
  source TEXT NOT NULL,
  UNIQUE(identity_id, normalized, source)
);

CREATE INDEX IF NOT EXISTS idx_identity_alias_norm ON identity_search_aliases(normalized);

CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identity_id TEXT NOT NULL REFERENCES identities(identity_id) ON DELETE CASCADE,
  source_skill_text_id TEXT,
  slot TEXT,
  uptie INTEGER,
  name_en TEXT,
  name_th TEXT,
  affinity TEXT,
  damage_type TEXT,
  skill_type TEXT,
  base_power INTEGER,
  coin_power INTEGER,
  coin_count INTEGER,
  deck_count INTEGER,
  attack_weight INTEGER,
  offense_level_json TEXT,
  description_en TEXT,
  description_th TEXT,
  mechanics_json TEXT,
  assets_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_skills_identity_uptie ON skills(identity_id, uptie);
CREATE INDEX IF NOT EXISTS idx_skills_text_id ON skills(source_skill_text_id);

CREATE TABLE IF NOT EXISTS coins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_row_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  coin_index INTEGER,
  effect_index INTEGER,
  text_en TEXT,
  text_th TEXT
);

CREATE TABLE IF NOT EXISTS passives (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identity_id TEXT NOT NULL REFERENCES identities(identity_id) ON DELETE CASCADE,
  passive_type TEXT,
  source_passive_text_id TEXT,
  name_en TEXT,
  name_th TEXT,
  requirement TEXT,
  description_en TEXT,
  description_th TEXT
);

CREATE TABLE IF NOT EXISTS status_effects (
  status_key TEXT PRIMARY KEY,
  name_en TEXT,
  name_th TEXT,
  desc_en TEXT,
  desc_th TEXT,
  summary_en TEXT,
  summary_th TEXT,
  icon_path TEXT,
  category TEXT,
  raw_en_json TEXT,
  raw_th_json TEXT
);

CREATE TABLE IF NOT EXISTS panic_info (
  panic_id TEXT PRIMARY KEY,
  name_en TEXT,
  name_th TEXT,
  low_morale_en TEXT,
  low_morale_th TEXT,
  panic_en TEXT,
  panic_th TEXT,
  source_file TEXT,
  raw_en_json TEXT,
  raw_th_json TEXT
);
CREATE TABLE IF NOT EXISTS mental_conditions (
  condition_id TEXT PRIMARY KEY,
  add_en TEXT,
  add_th TEXT,
  min_en TEXT,
  min_th TEXT,
  source_file TEXT,
  raw_en_json TEXT,
  raw_th_json TEXT
);
CREATE TABLE IF NOT EXISTS localization_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_key TEXT NOT NULL,
  category TEXT NOT NULL,
  language TEXT NOT NULL,
  field_name TEXT NOT NULL,
  text TEXT,
  source_file TEXT
);

CREATE INDEX IF NOT EXISTS idx_localization_lookup ON localization_entries(source_key, category, language);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_type TEXT NOT NULL,
  target_key TEXT NOT NULL,
  path TEXT NOT NULL,
  metadata_json TEXT,
  UNIQUE(asset_type, target_key, path)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


