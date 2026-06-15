from datetime import date, datetime, timedelta
from ..db import exdb
from ..processors.performance import compute_calendar_atl_history, compute_load_metrics, compute_injury_risk, compute_recovery
from .muscle_service import get_muscle_baselines, get_all_previous_fatigue, apply_decay, compute_days_since
from config import Config

def get_training_load_history(user_id, start_date=None, end_date=None, days=365):
    conn = exdb.connect()
    cursor = conn.cursor()

    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date = date.today() - timedelta(days=days)

    if end_date:
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_date = date.today()

    cursor.execute("""
    SELECT 
        date,
        training_load
    FROM activities
    WHERE date >= %s AND date <= %s
    ORDER BY date
""", (start_date, end_date))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows

def get_performance_history(user_id, start_date=None, end_date=None, days=365):
    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date = date.today() - timedelta(days=days)

    if end_date:
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_date = date.today()

    # Use a large buffer for warm-up so EWMA/CTL have long-term context
    buffer_start = start_date - timedelta(days=days)
    # Read configured scale and pass through to the processor
    scale = getattr(Config, 'TRAINING_LOAD_SCALE', 1.0)
    atl_tau = getattr(Config, 'TRAINING_ATL_TAU', 7)
    ctl_tau = getattr(Config, 'TRAINING_CTL_TAU', 42)
    history = get_training_load_history(user_id, start_date=buffer_start, end_date=end_date)
    return compute_calendar_atl_history(history, start_date=start_date, end_date=end_date, training_load_scale=scale, atl_tau=atl_tau, ctl_tau=ctl_tau)


def get_current_fatigue(user_id):
    conn = exdb.connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT muscle, fatigue
        FROM muscle_fatigue
        WHERE user_id=%s
    """, (user_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {r[0]: r[1] for r in rows}

def get_performance_summary(user_id):
    history = get_training_load_history(user_id)
    scale = getattr(Config, 'TRAINING_LOAD_SCALE', 1.0)
    atl_tau = getattr(Config, 'TRAINING_ATL_TAU', 7)
    ctl_tau = getattr(Config, 'TRAINING_CTL_TAU', 42)

    calendar_history = compute_calendar_atl_history(history, training_load_scale=scale, atl_tau=atl_tau, ctl_tau=ctl_tau)
    atl = calendar_history[-1]["atl"] if calendar_history else 0
    ctl = calendar_history[-1]["ctl"] if calendar_history else 0
    # _, ctl = compute_load_metrics(history, training_load_scale=scale)
    # Fetch stored fatigue rows (include last_updated) and apply decay to bring values to today
    stored = get_all_previous_fatigue(user_id)
    decayed_fatigue = {}
    for muscle, row in stored.items():
        raw = row.get("fatigue", 0.0) if row else 0.0
        last_updated = row.get("last_updated") if row else None
        days = compute_days_since(last_updated)
        try:
            decayed = apply_decay(float(raw), days)
        except Exception:
            decayed = float(raw or 0.0)
        decayed_fatigue[muscle] = decayed

    # Compute per-muscle baselines and ratios (decayed_current / baseline)
    baselines = get_muscle_baselines()
    ratios = {}
    for muscle, current in decayed_fatigue.items():
        base = baselines.get(muscle) or 0
        try:
            ratios[muscle] = float(current) / float(base) if base and base > 0 else 0.0
        except Exception:
            ratios[muscle] = 0.0

    form = ctl - atl
    injury_risk = compute_injury_risk(atl, ctl)
    recovery = compute_recovery(decayed_fatigue, baselines, history, evaluation_date=date.today())

    return {
        "fatigue": decayed_fatigue,
        "baselines": baselines,
        "ratios": ratios,
        "atl": atl,
        "ctl": ctl,
        "training_load_scale": scale,
        "form": form,
        "injury_risk": injury_risk,
        "recovery": recovery
    }