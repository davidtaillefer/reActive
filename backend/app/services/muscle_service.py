from collections import defaultdict
import pymysql
import difflib
import json
from datetime import datetime, timezone, date

from ..db import exdb
from ..utils.user_utils import get_user_uuid

# cache variables (module-level)
_cached_muscle_map = None
_cached_lookup_map = None

BODYWEIGHT_FACTORS = {
    "push_up": 0.65,
    "pull_up": 1.0,
    "chin_up": 1.0,
    "dip": 0.9,
    "sit_up": 0.4,
    "crunch": 0.35,
    "plank": 0.3,   # per second later
    "lunge": 0.75,
    "squat": 0.8
}

def estimate_bodyweight_load(exercise_name, reps, duration, user_weight):
    name = (exercise_name or "").lower().replace(" ", "_")

    factor = BODYWEIGHT_FACTORS.get(name, 0.5)  # fallback

    # Static holds (plank etc.)
    if name == "plank":
        return duration * factor * user_weight * 0.1

    if reps:
        return reps * factor * user_weight

    return 0


def compute_set_load(set_data, user_weight=None):
    weight = set_data.get("weight")
    reps = set_data.get("reps")
    duration = set_data.get("duration")
    exercise = set_data.get("exercise_name")

    # Weighted exercise
    if weight and weight > 0:
        return weight * (reps or 1)

    # Bodyweight fallback
    if user_weight:
        return estimate_bodyweight_load(exercise, reps, duration, user_weight)

    return 0


def load_exercise_map(): #add force_refresh=False
    
    # global _cached_muscle_map, _cached_lookup_map

    # if not force_refresh and _cached_muscle_map and _cached_lookup_map:
    #     return _cached_muscle_map, _cached_lookup_map
    
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # --------------------------------------------------
    # 1. BASE MAP (exercise_categories)
    # --------------------------------------------------
    cursor.execute("""
        SELECT 
            ec.name AS exercise,
            mg.name AS muscle,
            ecm.role
        FROM exercise_category_muscles ecm
        JOIN exercise_categories ec 
            ON ecm.exercise_category_id = ec.id
        JOIN muscle_groups mg 
            ON ecm.muscle_id = mg.id
    """)
    category_rows = cursor.fetchall()

    base_map = defaultdict(list)

    for r in category_rows:
        base_map[r["exercise"].lower()].append({
            "muscle": r["muscle"],
            "role": r["role"]
        })

    # --------------------------------------------------
    # 2. SPECIFIC MAP (exercise-level exceptions)
    # --------------------------------------------------
    cursor.execute("""
        SELECT 
            e.name AS exercise,
            mg.name AS muscle,
            em.role
        FROM exercise_muscles em
        JOIN exercises e 
            ON em.exercise_id = e.id
        JOIN muscle_groups mg 
            ON em.muscle_id = mg.id
    """)
    exercise_rows = cursor.fetchall()

    specific_map = defaultdict(list)

    for r in exercise_rows:
        specific_map[r["exercise"].lower()].append({
            "muscle": r["muscle"],
            "role": r["role"]
        })

    # --------------------------------------------------
    # 3. EXERCISE LOOKUP MAP (KEY ADDITION)
    # --------------------------------------------------
    cursor.execute("""
        SELECT 
            e.name AS exercise,
            e.garmin_exercise_id AS subtype,
            ec.name AS category
        FROM exercises e
        JOIN exercise_categories ec
            ON e.category_id = ec.id
        WHERE e.garmin_exercise_id IS NOT NULL
    """)
    lookup_rows = cursor.fetchall()

    exercise_lookup = {}

    for r in lookup_rows:
        key = (r["category"].lower(), int(r["subtype"]))
        exercise_lookup[key] = r["exercise"].lower()

    cursor.close()
    conn.close()

    # --------------------------------------------------
    # 4. MERGE MUSCLE MAPS (unchanged)
    # --------------------------------------------------
    final_map = dict(base_map)

    for exercise, muscles in specific_map.items():
        final_map[exercise] = muscles

    # --------------------------------------------------
    # DEBUG PRINTS
    # --------------------------------------------------
    print("\n=== MUSCLE MAP ===\n")
    for exercise in sorted(final_map.keys()):
        print(f"{exercise}:")
        for m in final_map[exercise]:
            print(f"  - {m['muscle']} ({m.get('role','unknown')})")
        print()

    print(f"Total entries: {len(final_map)}\n")

    print("\n=== LOOKUP MAP (category + subtype → exercise) ===\n")
    for k, v in list(exercise_lookup.items())[:20]:
        print(f"{k} → {v}")

    print(f"Total lookup entries: {len(exercise_lookup)}\n")
    
    # _cached_muscle_map = final_map
    # _cached_lookup_map = exercise_lookup

    return final_map, exercise_lookup

def compute_muscle_load(sets, exercise_map):
    muscle_load = {}

    for s in sets:
        raw_name = s.exercise_name or ""
        raw_category = s.exercise_category or ""
        match = match_exercise(raw_name, exercise_map)
        
        if not match:
            match = match_exercise(raw_category, exercise_map)

            if not match:
                print("No match found for exercise:", raw_category)
                continue
        
        user_weight = 82

        set_data = {
            "weight": s.weight,
            "reps": s.reps,
            "duration": getattr(s, "duration", None),
            "exercise_name": raw_name
        }

        volume = compute_set_load(set_data, user_weight)

        for m in exercise_map[match]:
            multiplier = 1.0 if m["role"] == "primary" else 0.5

            muscle = m["muscle"]
            muscle_load[muscle] = muscle_load.get(muscle, 0) + volume * multiplier

    return muscle_load

def normalise_name(name: str) -> str:
    return name.lower().strip()


def match_exercise(name, exercise_map):
    name = normalise_name(name)

    if name in exercise_map:
        return name

    # fuzzy match
    matches = difflib.get_close_matches(
        name,
        exercise_map.keys(),
        n=1,
        cutoff=0.7
    )

    return matches[0] if matches else None

# def get_muscle_activation(exercise_names):
#     query = """
#         SELECT m.name, em.role
#         FROM exercises e
#         JOIN exercise_muscles em ON e.id = em.exercise_id
#         JOIN muscles m ON m.id = em.muscle_id
#         WHERE e.name IN %s
#     """
    
DECAY_RATE = 0.85  # daily recovery

def apply_decay(fatigue, days=1):
    return fatigue * (DECAY_RATE ** (days*3))


def get_all_previous_fatigue(user_id):
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT * FROM muscle_fatigue WHERE user_id=%s",
        (user_id,)
    )
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {r["muscle"]: r for r in rows}


def update_muscle_fatigue(user_id, muscle_loads, workout_date=None):
    """
    muscle_loads = { "chest": 1200, "triceps": 800 }
    """
    if workout_date is None:
        workout_date = datetime.now(timezone.utc)
    elif isinstance(workout_date, str):
        workout_date = datetime.fromisoformat(workout_date.replace("Z", "+00:00"))

    # Ensure workout_date is timezone-aware or naive consistently
    if isinstance(workout_date, datetime) and workout_date.tzinfo is None:
        workout_date = workout_date.replace(tzinfo=timezone.utc)

    # 1. Fetch all existing muscle fatigue for the user
    existing_fatigue = get_all_previous_fatigue(user_id)

    # 2. Get list of all muscles we care about (new loads + existing fatigue that needs to decay)
    all_muscles = set(muscle_loads.keys()) | set(existing_fatigue.keys())

    updated = {}

    for muscle in all_muscles:
        existing = existing_fatigue.get(muscle)
        
        prev_fatigue = existing.get("fatigue", 0.0) if existing else 0.0
        last_updated = existing.get("last_updated") if existing else None
        
        # Calculate days since last_updated to workout_date
        if last_updated:
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated)
            elif isinstance(last_updated, date) and not isinstance(last_updated, datetime):
                last_updated = datetime.combine(last_updated, datetime.min.time())
                
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
                
            # If last_updated is in the future compared to workout_date (e.g. out of order upload), clamp days to 0
            delta = workout_date - last_updated if isinstance(workout_date, datetime) else datetime.combine(workout_date, datetime.min.time()).replace(tzinfo=timezone.utc) - last_updated
            days = max(0.0, delta.total_seconds() / 86400)
        else:
            days = 0.0

        recovered = apply_decay(prev_fatigue, days)
        load = muscle_loads.get(muscle, 0.0)
        new_fatigue = recovered + load

        updated[muscle] = new_fatigue

    # 3. Save all updated fatigue values to DB with the workout date
    save_fatigue(user_id, updated, workout_date)

    return updated

def get_previous_fatigue(user_id, muscle):
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT * FROM muscle_fatigue WHERE user_id=%s AND muscle=%s",
        (user_id, muscle)
    )
    
    rows = cursor.fetchone()
    cursor.close()
    conn.close()
    
    print("Existing DB entry:", rows)
    return rows

def save_fatigue(user_uuid, fatigue_dict, last_updated_date=None):
    if last_updated_date is None:
        last_updated_date = datetime.now(timezone.utc)
        
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    for muscle, value in fatigue_dict.items():
        cursor.execute("""
            INSERT INTO muscle_fatigue (user_id, muscle, fatigue, last_updated)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                fatigue = VALUES(fatigue),
                last_updated = VALUES(last_updated)
        """, (user_uuid, muscle, value, last_updated_date))

    conn.commit()
    cursor.close()
    conn.close()

def compute_days_since(last_updated):
    """
    Returns number of days (float) since last_updated timestamp.
    Handles None safely.
    """
    if not last_updated:
        return 0

    if isinstance(last_updated, str):
        # handle ISO strings from DB
        last_updated = datetime.fromisoformat(last_updated)
    elif isinstance(last_updated, date) and not isinstance(last_updated, datetime):
        last_updated = datetime.combine(last_updated, datetime.min.time())

    now = datetime.now(timezone.utc)

    # Ensure both are timezone-aware or naive consistently
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)

    delta = now - last_updated
    return max(0.0, delta.total_seconds() / 86400)  # days as float

def get_muscle_baselines():
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT muscle, AVG(`load`) as avg_load
        FROM activity_muscle_loads
        WHERE `load` > 0
        GROUP BY muscle
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {r["muscle"]: r["avg_load"] for r in rows}