import math
from datetime import datetime, timedelta
import os
from pyexpat.errors import messages
import xmltodict
from collections import deque

from typing import Optional, List, Dict
from ..parsers.fit_parser import parse_fit
from app.services.muscle_service import load_exercise_map, compute_muscle_load
from types import SimpleNamespace
from ..parsers.tcx_parser import parse_tcx
from ..processors.activity import finalize_activity
from ..serializers import activity_to_dict
from lib.metrics_availability import compute_metrics_availability
from flask import Blueprint, current_app, request
import json
from garmin_fit_sdk import Decoder, Stream

hrm_bp = Blueprint("hrm", __name__)  

def compute_grade_distance_based(track, i, min_distance=10):
    """
    Compute grade using accumulated distance (metres)
    instead of adjacent points
    """

    keys = sorted(track.keys())
    curr = track[keys[i]]

    lat2 = curr.get("position_lat")
    lon2 = curr.get("position_long")
    alt2 = curr.get("altitude_smooth")

    if None in (lat2, lon2, alt2):
        return None

    distance_accum = 0

    # Walk backwards until we hit min_distance
    for j in range(i - 1, -1, -1):
        prev = track[keys[j]]

        lat1 = prev.get("position_lat")
        lon1 = prev.get("position_long")
        alt1 = prev.get("altitude_smooth")

        if None in (lat1, lon1, alt1):
            continue

        d = haversine(lat1, lon1, lat2, lon2)
        distance_accum += d

        if distance_accum >= min_distance:
            elevation_delta = alt2 - alt1

            if distance_accum == 0:
                return None

            grade = (elevation_delta / distance_accum) * 100

            # Hard clamp to realistic values
            return max(min(grade, 30), -30)

    return None

def grade_bucket(g):
    if g is None:
        return None
    if g < -10:
        return "<-10%"
    elif g < -5:
        return "-10% to -5%"
    elif g < 0:
        return "-5% to 0%"
    elif g < 5:
        return "0% to 5%"
    elif g < 10:
        return "5% to 10%"
    elif g < 15:
        return "10% to 15%"
    else:
        return ">15%"
    
def smooth_elevation(track, window=5):
    keys = sorted(track.keys())
    alts = [track[k].get("enhanced_altitude") for k in keys]

    smoothed = []

    for i in range(len(alts)):
        vals = [
            a for a in alts[max(0, i-window):i+window+1]
            if a is not None
        ]

        if vals:
            smoothed.append(sum(vals) / len(vals))
        else:
            smoothed.append(None)

    for k, alt in zip(keys, smoothed):
        track[k]["enhanced_altitude"] = alt
        
def is_moving(point, min_speed=1.0):
    """
    min_speed in m/s (~3.6 km/h)
    """
    speed = point.get("enhanced_speed")
    if speed is None:
        return True  # fallback if speed missing
    return speed >= min_speed

# GET the contents of an HRM file

@hrm_bp.route("/hrm/<hrmfile>")
def readhrm(hrmfile):
    file_name, file_extension = os.path.splitext(hrmfile)
    gps_base_path = os.path.join(current_app.config["BASE_DATA_DIR"], "gps")

    if file_extension == ".tcx":
        base_path = os.path.join(gps_base_path, "tcx")
        activity = parse_tcx(os.path.join(base_path, hrmfile))
    elif file_extension == ".fit":
        base_path = os.path.join(gps_base_path, "fit")
        activity = parse_fit(os.path.join(base_path, hrmfile))
    else:
        return {"error": "Unsupported file type"}, 400

    activity.name = finalize_activity(activity)

    d = activity_to_dict(activity)

    # If a sidecar sets JSON exists (from edits), load and replace sets
    try:
        if file_extension == ".fit":
            sidecar_path = os.path.join(gps_base_path, "fit", f"{file_name}.sets.json")
        else:
            sidecar_path = os.path.join(gps_base_path, "tcx", f"{file_name}.sets.json")

        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r') as sf:
                side_sets = json.load(sf)
                if isinstance(side_sets, list):
                    d["sets"] = side_sets

                    # Recompute muscle loads from edited sets so downstream UI (muscle map) uses updated data
                    try:
                        # convert dicts to objects expected by compute_muscle_load
                        converted = [SimpleNamespace(**s) if isinstance(s, dict) else s for s in side_sets]
                        exercise_map, exercise_lookup = load_exercise_map()
                        muscle_loads = compute_muscle_load(converted, exercise_map)
                        if muscle_loads:
                            d["muscles"] = {"load": muscle_loads}
                    except Exception:
                        # ignore muscle recompute errors
                        pass
    except Exception:
        # ignore sidecar read errors
        pass

    # compute metrics availability from serialized track
    track = d.get("track", []) or []

    d["metricsAvailability"] = compute_metrics_availability(track, d.get("muscles"))

    return d



@hrm_bp.route("/hrm/<hrmfile>/sets", methods=["POST"])
def save_hrm_sets(hrmfile):
    """Save edited sets to a sidecar JSON file next to the original HRM file."""
    try:
        payload = request.get_json()
        sets = payload.get('sets') if payload else None
        if not isinstance(sets, list):
            return {"error": "Invalid payload"}, 400

        file_name, file_extension = os.path.splitext(hrmfile)
        gps_base_path = os.path.join(current_app.config["BASE_DATA_DIR"], "gps")

        if file_extension == ".fit":
            base_path = os.path.join(gps_base_path, "fit")
        elif file_extension == ".tcx":
            base_path = os.path.join(gps_base_path, "tcx")
        else:
            return {"error": "Unsupported file type"}, 400

        sidecar_path = os.path.join(base_path, f"{file_name}.sets.json")
        with open(sidecar_path, 'w') as sf:
            json.dump(sets, sf)

        return {"status": "ok"}
    except Exception as e:
        current_app.logger.exception('failed to save sets')
        return {"error": "failed to save sets"}, 500