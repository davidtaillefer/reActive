import math
from datetime import datetime
from ..models import Climb

# def compute_grades(records):
#     prev = None

#     for r in records:
#         if prev and all([
#             prev.position_lat, prev.position_long,
#             r.position_lat, r.position_long,
#             prev.enhanced_altitude, r.enhanced_altitude
#         ]):
#             dist = haversine(
#                 prev.position_lat, prev.position_long,
#                 r.position_lat, r.position_long
#             )

#             if dist > 0:
#                 r.grade = ((r.enhanced_altitude - prev.enhanced_altitude) / dist) * 100
#                 r.grade_bucket = grade_bucket(r.grade)

#         prev = r
        

# def smooth_grades(records, window=5):
#     for i in range(len(records)):
#         vals = [
#             records[j].grade
#             for j in range(max(0, i-window), min(len(records), i+window+1))
#             if records[j].grade is not None
#         ]

#         records[i].grade_smooth = sum(vals)/len(vals) if vals else None
            
def grade_stats(track):
    if isinstance(track, dict): 
        iterable = track.values()
    else:
        iterable = track

    values = []

    for p in iterable:
        if not isinstance(p, dict):
            continue

        g = p.get("grade_smooth", None)
        if isinstance(g, (int, float)):
            values.append(g)

    if not values:
        return None, None

    values.sort()

    n = len(values)
    low = values[int(n * 0.02)]
    high = values[int(n * 0.98)]

    return round(low, 2), round(high, 2)

# --- Enhanced Grade Computation ---
def compute_and_smooth_grades(records, window_meters=20):
    """
    Computes point-to-point grades and applies a robust distance-based
    smoothing window to isolate sharp, micro-climbing efforts accurately.
    """
    n = len(records)
    if n < 2:
        return

    # 1. Compute raw point-to-point metrics
    for i in range(1, n):
        prev, curr = records[i-1], records[i]
        if all([prev.position_lat, prev.position_long, curr.position_lat, curr.position_long,
                prev.enhanced_altitude, curr.enhanced_altitude]):
            
            dist = haversine(prev.position_lat, prev.position_long, curr.position_lat, curr.position_long)
            if dist > 0:
                curr.grade = ((curr.enhanced_altitude - prev.enhanced_altitude) / dist) * 100
                curr.grade_bucket = grade_bucket(curr.grade)


    # 2. Distance-based smoothing (Ensures granular profile stability)
    for i in range(n):
        curr = records[i]
        if curr.distance is None or curr.enhanced_altitude is None:
            continue

        # Look forward until we span the physical window distance threshold
        j = i
        while j < n - 1 and (records[j].distance - curr.distance) < window_meters:
            j += 1

        delta_dist = records[j].distance - curr.distance
        delta_alt = records[j].enhanced_altitude - curr.enhanced_altitude

        if delta_dist > 1.5:  # Guard against mathematical division anomalies during stops
            curr.grade_smooth = max(-30.0, min(35.0, (delta_alt / delta_dist) * 100))
        else:
            curr.grade_smooth = curr.grade if curr.grade is not None else 0.0


# --- Climb Identification and Strava Categorization Routine ---
def determine_strava_category(length_m, avg_grade_pct):
    if length_m < 500 or avg_grade_pct < 3.0:
        return "Uncategorized"
    
    score = length_m * avg_grade_pct
    if score >= 80000: return "HC (Hors Catégorie)"
    elif score >= 64000: return "Category 1"
    elif score >= 32000: return "Category 2"
    elif score >= 16000: return "Category 3"
    elif score >= 8000: return "Category 4"
    return "Uncategorized"


def extract_activity_climbs(activity, termination_buffer_m=50):
    """
    Scans the track array inside an Activity object, isolates sustained climbs,
    and updates the activity object with fully calculated Climb dataclasses.
    """
    track = activity.track
    n = len(track)
    if n < 2:
        return

    in_climb = False
    climb_start_idx = None
    flat_distance_accumulator = 0.0

    for i in range(1, n):
        curr, prev = track[i], track[i-1]
        if curr.distance is None or curr.grade_smooth is None or prev.distance is None:
            continue

        dist_delta = curr.distance - prev.distance

        if not in_climb:
            # Trigger: Sustained kick starting above 3.5%
            if curr.grade_smooth >= 3.5:
                in_climb = True
                climb_start_idx = i
                flat_distance_accumulator = 0.0
        else:
            # Accumulate flat/descending segments inside the active climb tracking loop
            if curr.grade_smooth < 1.5:
                flat_distance_accumulator += dist_delta
            else:
                flat_distance_accumulator = 0.0

            # Termination sequence check
            if flat_distance_accumulator >= termination_buffer_m or i == n - 1:
                # Wind back index to strip trailing flat/descent noise out of the segment calculations
                end_idx = i
                while end_idx > climb_start_idx and (track[i].distance - track[end_idx].distance) < flat_distance_accumulator:
                    if track[end_idx].grade_smooth is not None and track[end_idx].grade_smooth >= 1.5:
                        break
                    end_idx -= 1

                start_rec, end_rec = track[climb_start_idx], track[end_idx]
                total_dist = end_rec.distance - start_rec.distance
                total_gain = end_rec.enhanced_altitude - start_rec.enhanced_altitude
                avg_grade = (total_gain / total_dist) * 100 if total_dist > 0 else 0.0

                # Check if it satisfies standard definitions (500m length baseline)
                if total_dist >= 500.0 and total_gain >= 15.0:
                    climb_records = track[climb_start_idx:end_idx + 1]
                    
                    # Capture maximum grade of the climb accurately using your smoothed data
                    max_grade = max((r.grade_smooth for r in climb_records if r.grade_smooth is not None), default=0.0)
                    category = determine_strava_category(total_dist, avg_grade)

                    activity.climbs.append(Climb(
                        start_index=climb_start_idx,
                        end_index=end_idx,
                        start_timestamp=start_rec.timestamp,
                        end_timestamp=end_rec.timestamp,
                        distance_m=round(total_dist, 1),
                        elevation_gain_m=round(total_gain, 1),
                        avg_grade_pct=round(avg_grade, 2),
                        max_grade_pct=round(max_grade, 1),
                        climb_score=round(total_dist * avg_grade, 1),
                        category=category
                    ))

                # Reset status flags
                in_climb = False
                climb_start_idx = None
                flat_distance_accumulator = 0.0

    # Sync summary global activity fields
    all_grades = [r.grade_smooth for r in track if r.grade_smooth is not None]
    if all_grades:
        activity.grade_max = round(max(all_grades), 1)
        activity.grade_min = round(min(all_grades), 1)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def grade_bucket(g):
    if g is None:
        return None
    if g < -10:
        return "<-10%"
    elif g < -5:
        return "-10% to -5%"
    elif g < 0:
        return "-5% to 0%"
    elif g < 3:
        return "0% to 3%"
    elif g < 6:
        return "3% to 6%"
    elif g < 9:
            return "6% to 9%"
    elif g < 12:
            return "9% to 12%"
    elif g < 15:
            return "12% to 15%"
    else:
        return ">15%"
