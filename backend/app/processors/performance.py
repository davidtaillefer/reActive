from datetime import date, datetime, timedelta
import math

# def ewma(values, tau):
#     alpha = 2 / (tau + 1)
#     result = []

#     prev = values[0] if values else 0
#     for v in values:
#         prev = alpha * v + (1 - alpha) * prev
#         result.append(prev)

#     return result


def aggregate_daily_loads(loads):
    daily = {}

    for row in loads:
        if isinstance(row, dict):
            date_value = row.get("date") or row.get("activity_date") or row.get("day")
            load = row.get("training_load") or row.get("load") or 0
        else:
            date_value = row[0] if len(row) > 0 else None
            load = row[1] if len(row) > 1 and row[1] is not None else 0

        if date_value is None:
            continue

        if hasattr(date_value, "isoformat"):
            date_str = date_value.isoformat().split("T")[0]
        else:
            date_str = str(date_value).split("T")[0]

        try:
            daily[date_str] = daily.get(date_str, 0) + float(load)
        except (TypeError, ValueError):
            continue

    return sorted(daily.items())


def compute_calendar_atl_history(loads, start_date=None, end_date=None, buffer_days=365, atl_tau=7, ctl_tau=42, training_load_scale=1.0):
    daily = {date: load for date, load in aggregate_daily_loads(loads)}

    if start_date is None or end_date is None:
        if daily:
            dates = [date for date, _ in sorted(daily.items())]
            if start_date is None:
                start_date = datetime.strptime(dates[0], "%Y-%m-%d").date()
            if end_date is None:
                #end_date = datetime.strptime(dates[-1], "%Y-%m-%d").date()
                end_date = date.today()
        else:
            return []

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Use standard EWMA alpha for ATL and CTL with configurable taus
    alpha_atl = 2 / (atl_tau + 1)
    alpha_ctl = 2 / (ctl_tau + 1)

    buffer_start = start_date - timedelta(days=buffer_days)
    current = buffer_start
    atl = 0.0
    ctl = 0.0
    history = []

    while current <= end_date:
        d_str = current.isoformat()
        load = daily.get(d_str, 0)

        # Apply configured scale to stored training_load values before EWMA
        scaled_load = load * float(training_load_scale or 1.0)

        # Standard EWMA updates (use scaled load)
        atl = (alpha_atl * scaled_load) + ((1 - alpha_atl) * atl)
        ctl = (alpha_ctl * scaled_load) + ((1 - alpha_ctl) * ctl)

        if current >= start_date:
            history.append({
                "date": d_str,
                "load": load,
                "scaled_load": scaled_load,
                "atl": atl,
                "ctl": ctl,
            })

        current += timedelta(days=1)

    return history


def compute_load_history(loads, atl_tau=7, ctl_tau=42, training_load_scale=1.0):
    aggregated = aggregate_daily_loads(loads)
    if not aggregated:
        return []

    daily_history = []
    atl = 0.0
    ctl = 0.0
    alpha_atl = 2 / (atl_tau + 1)
    alpha_ctl = 2 / (ctl_tau + 1)

    for date_str, load in aggregated:
        scaled_load = load * float(training_load_scale or 1.0)
        atl = alpha_atl * scaled_load + (1 - alpha_atl) * atl
        ctl = alpha_ctl * scaled_load + (1 - alpha_ctl) * ctl
        daily_history.append({
            "date": date_str,
            "load": load,
            "scaled_load": scaled_load,
            "atl": atl,
            "ctl": ctl,
        })

    return daily_history


def compute_load_metrics(loads, training_load_scale=1.0):
    """Accepts `loads` as a list of DB rows (tuples) or dicts.

    If the rows already contain `atl`/`ctl`, return those from the
    most-recent row. Otherwise compute EWMA on a per-day `load` value.
    Returns a tuple `(atl, ctl)`.
    """
    if not loads:
        return 0, 0

    history = compute_load_history(loads, training_load_scale=training_load_scale)
    if not history:
        return 0, 0

    last = history[-1]
    return last["atl"], last["ctl"]
    
def compute_injury_risk(atl, ctl):
    if ctl == 0:
        return 0

    ratio = atl / ctl

    # simple but effective model
    if ratio < 0.8:
        return 0.2
    elif ratio < 1.3:
        return 0.5
    else:
        return min(1.0, 0.5 + (ratio - 1.3))
    
def compute_recovery(fatigue_map, baselines=None, loads=None, evaluation_date=None):
    """Compute recovery per muscle relative to historical baselines.
    
    If baselines are provided, each muscle's recovery is scored relative to
    how fatigued it is compared to its average historical load. A muscle at
    baseline fatigue = 50% recovered. Beyond 2x baseline = fully depleted.
    
    Falls back to the max-fatigue / absolute cap approach when no baselines exist.
    """
    if not fatigue_map:
        return {"overall": 1.0, "strength": 1.0, "cardio": 1.0, "per_muscle": {}}

    per_muscle_recovery = {}

    if baselines:
        for muscle, fatigue in fatigue_map.items():
            baseline = baselines.get(muscle)
            if baseline and baseline > 0:
                # ratio > 1 means more fatigued than average, 0 means fully fresh
                ratio = fatigue / baseline
                # Linear scale: 0 fatigue = 100% recovered, at 2x baseline = 0% recovered
                recovery = max(0.0, 1.0 - (ratio / 2.0))
            else:
                # No baseline for this muscle — use conservative 50% recovery
                recovery = 0.5
            per_muscle_recovery[muscle] = recovery

        if per_muscle_recovery:
            strength_recovery = sum(per_muscle_recovery.values()) / len(per_muscle_recovery)
        else:
            strength_recovery = 1.0
    else:
        # Fallback: no baselines yet, use absolute cap of 10000 volume units
        max_fatigue = max(fatigue_map.values())
        strength_recovery = max(0.0, 1.0 - (max_fatigue / 10000))
        per_muscle_recovery = {m: max(0.0, 1.0 - (v / 10000)) for m, v in fatigue_map.items()}

    # Cardio recovery: if historical training loads are provided, compute
    # fitness/fatigue/readiness using the Banister fitness-fatigue model.
    cardio_recovery = None
    if loads:
        # evaluation_date defaults to today
        if evaluation_date is None:
            evaluation_date = date.today()
        if isinstance(evaluation_date, str):
            evaluation_date = datetime.strptime(evaluation_date, "%Y-%m-%d").date()

        # aggregate provided loads into daily sums (returns list of (date_str, load))
        aggregated = aggregate_daily_loads(loads)

        # Build a daily map for quick lookup and iterate explicit days so we
        # correctly handle days with zero load up to the evaluation date.
        daily_map = {d: l for d, l in aggregated}
        
        def compute_readiness_for_date(eval_date):
            fitness = 0.0
            fatigue = 0.0

            # Use explicit windows: fitness over 42 days, fatigue over 7 days
            fitness_window_days = 42
            fatigue_window_days = 7

            # Sum fitness contributions (0..42 days ago)
            for d in range(0, fitness_window_days + 1):
                day = eval_date - timedelta(days=d)
                load = daily_map.get(day.isoformat(), 0.0)
                if load:
                    fitness += load * math.exp(-d / 42.0)

            # Sum fatigue contributions (0..7 days ago)
            for d in range(0, fatigue_window_days + 1):
                day = eval_date - timedelta(days=d)
                load = daily_map.get(day.isoformat(), 0.0)
                if load:
                    fatigue += load * math.exp(-d / 7.0)

            print(f"Readiness eval for {eval_date}: fitness={fitness:.2f}, fatigue={fatigue:.2f}, raw readiness={fitness - fatigue:.2f}")

            return fitness - fatigue

        raw_readiness = compute_readiness_for_date(evaluation_date)

        lookback_days = 7
        readiness_values = []
        for i in range(lookback_days):
            d = evaluation_date - timedelta(days=i)
            readiness_values.append(compute_readiness_for_date(d))

        min_r = min(readiness_values) if readiness_values else raw_readiness
        max_r = max(readiness_values) if readiness_values else raw_readiness

        if max_r - min_r == 0:
            readiness_percent = 50.0
        else:
            readiness_percent = ((raw_readiness - min_r) / (max_r - min_r)) * 100.0

        # clamp
        readiness_percent = max(0.0, min(100.0, readiness_percent))

        cardio_recovery = readiness_percent / 100.0

    # Fallback when loads not provided
    if cardio_recovery is None:
        cardio_recovery = 0.7 + (0.3 * strength_recovery)

    overall = (strength_recovery + cardio_recovery) / 2.0

    return {
        "overall": overall,
        "strength": strength_recovery,
        "cardio": cardio_recovery,
        "per_muscle": per_muscle_recovery
    }
