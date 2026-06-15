#!/usr/bin/env python3
"""
migrate_muscle_fatigue.py
-------------------------
Populates activity_muscle_loads by replaying all historical strength workouts
chronologically, then rebuilds muscle_fatigue from scratch based on that
history.

Run from the backend directory:
  ./venv/bin/python scripts/migrate_muscle_fatigue.py
"""
import os
import sys
import pymysql
from datetime import datetime, timezone, date

# Make sure app modules are importable from backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from garmin_fit_sdk import Decoder, Stream

# ── DB connection ────────────────────────────────────────────────────────────
def get_conn():
    return pymysql.connect(
        host=Config.MYSQL_DATABASE_HOST,
        user=Config.MYSQL_DATABASE_USER,
        password=Config.MYSQL_DATABASE_PASSWORD,
        database=Config.MYSQL_DATABASE_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

STRENGTH_SPORT_ID = 6
DECAY_RATE = 0.85   # daily recovery (matches muscle_service.py)
FIT_DIR = os.path.join(Config.BASE_DATA_DIR, "gps", "fit")

# ── Minimal FIT parser (no Flask context needed) ─────────────────────────────
BODYWEIGHT_FACTORS = {
    "push_up": 0.65, "pull_up": 1.0, "chin_up": 1.0, "dip": 0.9,
    "sit_up": 0.4, "crunch": 0.35, "plank": 0.3, "lunge": 0.75, "squat": 0.8
}
USER_WEIGHT = 82  # kg — matches current hardcoded value in muscle_service.py

def compute_set_load(weight, reps, duration, exercise_name):
    if weight and weight > 0:
        return weight * (reps or 1)
    name = (exercise_name or "").lower().replace(" ", "_")
    factor = BODYWEIGHT_FACTORS.get(name, 0.5)
    if name == "plank":
        return (duration or 0) * factor * USER_WEIGHT * 0.1
    return (reps or 0) * factor * USER_WEIGHT

def load_exercise_maps(conn):
    cursor = conn.cursor()
    # Category muscles
    cursor.execute("""
        SELECT ec.name AS exercise, mg.name AS muscle, ecm.role
        FROM exercise_category_muscles ecm
        JOIN exercise_categories ec ON ecm.exercise_category_id = ec.id
        JOIN muscle_groups mg ON ecm.muscle_id = mg.id
    """)
    base_map = {}
    for r in cursor.fetchall():
        base_map.setdefault(r["exercise"].lower(), []).append({"muscle": r["muscle"], "role": r["role"]})

    # Exercise-specific overrides
    cursor.execute("""
        SELECT e.name AS exercise, mg.name AS muscle, em.role
        FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id
        JOIN muscle_groups mg ON em.muscle_id = mg.id
    """)
    for r in cursor.fetchall():
        base_map[r["exercise"].lower()] = [{"muscle": r["muscle"], "role": r["role"]}]

    # Garmin lookup (category + subtype → exercise name)
    cursor.execute("""
        SELECT e.name AS exercise, e.garmin_exercise_id AS subtype, ec.name AS category
        FROM exercises e
        JOIN exercise_categories ec ON e.category_id = ec.id
        WHERE e.garmin_exercise_id IS NOT NULL
    """)
    lookup = {}
    for r in cursor.fetchall():
        lookup[(r["category"].lower(), int(r["subtype"]))] = r["exercise"].lower()

    cursor.close()
    return base_map, lookup

import difflib

def match_exercise(name, exercise_map):
    name = name.lower().strip()
    if name in exercise_map:
        return name
    matches = difflib.get_close_matches(name, exercise_map.keys(), n=1, cutoff=0.7)
    return matches[0] if matches else None

def parse_fit_muscle_loads(file_path, exercise_map, exercise_lookup):
    stream = Stream.from_file(file_path)
    decoder = Decoder(stream)
    messages, _ = decoder.read()

    muscle_load = {}

    for msg in messages.get("set_mesgs", []):
        category_raw = msg.get("category")
        category_raw = category_raw if isinstance(category_raw, str) else (str(category_raw[0]) if isinstance(category_raw, list) and category_raw else "")
        # print(f"DEBUG: category_raw = {category_raw}")
        subtype_raw = msg.get("category_subtype")
        subtype_raw = subtype_raw if isinstance(subtype_raw, int) else (int(subtype_raw[0]) if isinstance(subtype_raw, list) and subtype_raw else None)
        weight = msg.get("weight")
        reps = msg.get("repetitions")
        duration = msg.get("duration")

        if category_raw is None:
            continue

        category_str = str(category_raw).lower() if not isinstance(category_raw, str) else category_raw.lower()
        subtype_int = int(subtype_raw) if subtype_raw is not None else None

        # Resolve to exercise name
        exercise_name = None
        if subtype_int is not None:
            exercise_name = exercise_lookup.get((category_str, subtype_int))
        if not exercise_name:
            exercise_name = match_exercise(category_str, exercise_map)
        if not exercise_name:
            continue

        volume = compute_set_load(weight, reps, duration, exercise_name)
        if volume <= 0:
            continue

        muscles = exercise_map.get(exercise_name, [])
        for m in muscles:
            multiplier = 1.0 if m["role"] == "primary" else 0.5
            muscle_load[m["muscle"]] = muscle_load.get(m["muscle"], 0) + volume * multiplier

    return muscle_load

def apply_decay(fatigue, days):
    return fatigue * (DECAY_RATE ** days)

def to_datetime(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=timezone.utc)
    return None

# ── Main migration ────────────────────────────────────────────────────────────
def main():
    conn = get_conn()

    print("Loading exercise maps…")
    exercise_map, exercise_lookup = load_exercise_maps(conn)
    print(f"  {len(exercise_map)} exercises loaded.")

    print("Fetching user_id…")
    cursor = conn.cursor()
    cursor.execute("SELECT user_uuid FROM user_preferences LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    if not row:
        print("ERROR: No user_preferences row found — cannot determine user_id.")
        sys.exit(1)
    user_id = row["user_uuid"]
    print(f"  user_id = {user_id}")

    print("Fetching strength activities in chronological order…")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date, hrmfile FROM activities
        WHERE sport = %s AND hrmfile IS NOT NULL AND hrmfile != ''
        ORDER BY date ASC
    """, (STRENGTH_SPORT_ID,))
    activities = cursor.fetchall()
    cursor.close()
    print(f"  {len(activities)} strength activities found.")

    # Clear existing data so we start clean
    print("Clearing activity_muscle_loads and muscle_fatigue…")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activity_muscle_loads WHERE activity_id IN (SELECT id FROM activities WHERE sport = %s)", (STRENGTH_SPORT_ID,))
    cursor.execute("DELETE FROM muscle_fatigue WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()

    # Replay workouts chronologically
    fatigue_state = {}   # muscle → current fatigue value
    last_date = {}       # muscle → last update datetime

    parsed_ok = 0
    skipped = 0

    for act in activities:
        act_id = act["id"]
        act_date = to_datetime(act["date"])
        hrmfile = act["hrmfile"]

        fit_path = os.path.join(FIT_DIR, hrmfile)
        if not os.path.exists(fit_path):
            print(f"  [{act_id}] SKIP — file not found: {hrmfile}")
            skipped += 1
            continue

        try:
            muscle_loads = parse_fit_muscle_loads(fit_path, exercise_map, exercise_lookup)
        except Exception as e:
            print(f"  [{act_id}] SKIP — parse error: {e}")
            skipped += 1
            continue

        if not muscle_loads:
            print(f"  [{act_id}] SKIP — no muscle loads extracted from {hrmfile}")
            skipped += 1
            continue

        # Save loads to activity_muscle_loads
        cursor = conn.cursor()
        for muscle, load in muscle_loads.items():
            cursor.execute("""
                INSERT INTO activity_muscle_loads (activity_id, muscle, `load`)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE `load` = VALUES(`load`)
            """, (act_id, muscle, load))
        conn.commit()
        cursor.close()

        # Collect all muscles (existing fatigue + new loads)
        all_muscles = set(muscle_loads.keys()) | set(fatigue_state.keys())

        for muscle in all_muscles:
            prev = fatigue_state.get(muscle, 0.0)
            prev_date = last_date.get(muscle)

            days = 0.0
            if prev_date and act_date:
                delta = act_date - prev_date
                days = max(0.0, delta.total_seconds() / 86400)

            recovered = apply_decay(prev, days)
            load = muscle_loads.get(muscle, 0.0)
            fatigue_state[muscle] = recovered + load
            last_date[muscle] = act_date

        muscle_summary = ", ".join(f"{m}: {v:.0f}" for m, v in sorted(muscle_loads.items()))
        print(f"  [{act_id}] {act_date.date()} OK  — {muscle_summary}")
        parsed_ok += 1

    # Write final fatigue state to muscle_fatigue table
    print(f"\nSaving final fatigue state ({len(fatigue_state)} muscles)…")
    cursor = conn.cursor()
    for muscle, fatigue in fatigue_state.items():
        ld = last_date.get(muscle, datetime.now(timezone.utc))
        cursor.execute("""
            INSERT INTO muscle_fatigue (user_id, muscle, fatigue, last_updated)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                fatigue = VALUES(fatigue),
                last_updated = VALUES(last_updated)
        """, (user_id, muscle, fatigue, ld))
    conn.commit()
    cursor.close()

    conn.close()

    print(f"\nDone! Parsed: {parsed_ok}  Skipped: {skipped}")
    print("muscle_fatigue and activity_muscle_loads have been rebuilt from history.")

if __name__ == "__main__":
    main()
