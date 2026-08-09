import os
import pymysql
from ..db import exdb
from flask import Blueprint, jsonify, request, current_app
from ..utils.auth import login_required
from ..utils.user_utils import get_user_uuid
from datetime import datetime, timedelta
from ..parsers.fit_parser import parse_fit
from ..services.muscle_service import update_muscle_fatigue

activities_bp = Blueprint('activities', __name__)

STRENGTH_SPORT_ID = 6  # 'Strength' in the sports table

def save_activity_muscle_loads(activity_id, muscle_loads):
    """Persist per-muscle loads for a strength activity."""
    if not muscle_loads:
        return
    conn = exdb.connect()
    cursor = conn.cursor()
    for muscle, load in muscle_loads.items():
        cursor.execute("""
            INSERT INTO activity_muscle_loads (activity_id, muscle, `load`)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE `load` = VALUES(`load`)
        """, (activity_id, muscle, load))
    conn.commit()
    cursor.close()
    conn.close()

def trigger_muscle_fatigue_update(user_id, hrmfile, workout_date):
    """Parse the FIT file and update muscle fatigue in the database."""
    try:

        gps_base_path = os.path.join(current_app.config["BASE_DATA_DIR"], "gps", "fit")
        file_path = os.path.join(gps_base_path, hrmfile)

        if not os.path.exists(file_path):
            print(f"[muscle fatigue] FIT file not found: {file_path}")
            return None

        activity = parse_fit(file_path)
        muscle_loads = activity.muscles.get("load", {}) if activity.muscles else {}

        if muscle_loads:
            update_muscle_fatigue(user_id, muscle_loads, workout_date=workout_date)
            return muscle_loads
        return None
    except Exception as e:
        print(f"[muscle fatigue] Error updating fatigue: {e}")
        return None


# Admin: flush exercise map cache
@activities_bp.route('/admin/cache/exercise_map/flush', methods=['POST'])
@login_required
def flush_exercise_map_cache():
    try:
        from ..services.muscle_service import invalidate_exercise_map_cache
        invalidate_exercise_map_cache()
        return jsonify({'status': 'ok', 'msg': 'exercise map cache flushed'})
    except Exception as e:
        print('Error flushing cache:', e)
        return jsonify({'status': 'error', 'msg': 'failed to flush cache'}), 500

# GET all activity records 
@activities_bp.route('/activities')
@login_required
def activities():
    conn = None
    cursor = None
    try:
        user_id = get_user_uuid()
        sport = request.args.get('sport')
        startdate = request.args.get('start')
        enddate = request.args.get('end')
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM activities WHERE user_id = %s AND (%s IS NULL OR sport = %s) AND date BETWEEN %s and %s"
        data = (user_id, sport, sport, startdate, enddate)
        cursor.execute(sql, data)
        activities = cursor.fetchall()
        print(f"[activities] user_id={user_id} fetched {len(activities)} activities (sport={sport} start={startdate} end={enddate})")
        for activity in activities:  
            activity['date'] = activity['date'] + timedelta(hours=activity['tzoffset'])
        res = jsonify(activities)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# GET an individual activity by id

@activities_bp.route('/activities/<int:activityid>')
@login_required
def activity(activityid):
    conn = None
    cursor = None
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = exdb.get_db().cursor() 
        user_id = get_user_uuid()
        sql = "SELECT * FROM activities WHERE id=%s AND user_id = %s"
        cursor.execute(sql, (activityid, user_id))
        activity = cursor.fetchone()
        print(f"[activities] fetch activity id={activityid} user_id={user_id} found={bool(activity)}")
        res = jsonify(activity)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# GET the most recent x activity records 
@activities_bp.route('/activities/recent/<int:number>')
@login_required
def recentactivities(number):
    conn = None
    cursor = None
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        user_id = get_user_uuid()
        sql = "SELECT * FROM activities WHERE user_id = %s ORDER BY date DESC LIMIT %s"
        cursor.execute(sql, (user_id, number))
        activities = cursor.fetchall()
        print(f"[activities] recent user_id={user_id} count={len(activities)}")
        for activity in activities: 
            activity['date'] = activity['date'] + timedelta(hours=activity['tzoffset'])
        res = jsonify(activities)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# Create new activity record        
@activities_bp.route('/activities', methods=['POST'])
@login_required
def createactivity():
    print("Received request to create activity with data:", request.get_json())
    conn = None
    cursor = None
    try:
        newrecord = request.get_json()
        sport = newrecord['sport']
        subsport = newrecord['subsport']
        raw = newrecord['date']

        # Handle Z → +00:00 for Python
        raw = raw.replace("Z", "+00:00")

        dt = datetime.fromisoformat(raw)

        # Convert to UTC (important before storing)
        dt_utc = dt  #.astimezone()

        # MySQL DATETIME format
        nd = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
        
        duration = newrecord['duration']
        intensity = newrecord['intensity']
        distance = newrecord['distance']
        avgspeed = newrecord['avgspeed']
        latitude = newrecord['latitude']
        if latitude == '':
            latitude = None
        longitude = newrecord['longitude']
        if longitude == '':
            longitude = None
        hrmfile = newrecord['hrmfile']
        equipment = newrecord['equipment']
        if equipment == '':
            equipment = None
        heartrate = newrecord['heartrate']
        if heartrate == '':
            heartrate = 0
        comments = newrecord['comments']
        ascent = newrecord['ascent']
        calories = newrecord['calories']
        avgcadence = newrecord['avgcadence']
        avgpower = newrecord['avgpower']
        device = newrecord['device']
        name = newrecord['name']
        training_load = newrecord['training_load']
        workout_feel = newrecord['workout_feel']
        workout_rpe = newrecord['workout_rpe']
        ate = newrecord['ate']
        ante = newrecord['ante']
        tzoffset = newrecord['offset']
        if tzoffset == '':
            tzoffset = 0
            
        print(f"Received new activity: Sport={sport}, Date={nd}, Duration={duration}, Training Load={training_load}")
    
        # insert activity record in database (associate with user)
        print("Inserting new activity into database...")
        user_id = get_user_uuid()
        print(f"User ID for new activity: {user_id}")
        sqlQuery = "INSERT INTO activities(user_id, sport, subsport, date, duration, intensity, distance, avgspeed, latitude, longitude, hrmfile, equipment, heartrate, comments, ascent, calories, avgcadence, avgpower, device, name, training_load, workout_feel, workout_rpe, ate, ante, tzoffset) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        data = (user_id, sport, subsport, nd, duration, intensity, distance, avgspeed, latitude, longitude, hrmfile, equipment, heartrate, comments, ascent, calories, avgcadence, avgpower, device, name, training_load, workout_feel, workout_rpe, ate, ante, tzoffset)
        conn = exdb.connect()
        cursor = exdb.get_db().cursor()
        cursor.execute(sqlQuery, data)
        conn.commit()
        new_activity_id = cursor.lastrowid

        # If this is a strength workout with a FIT file, update muscle fatigue
        if sport == STRENGTH_SPORT_ID and hrmfile:
            muscle_loads = trigger_muscle_fatigue_update(user_id, hrmfile, nd)
            if muscle_loads and new_activity_id:
                save_activity_muscle_loads(new_activity_id, muscle_loads)

        return jsonify({
                    'res': 'Activity created successfully.',
                    'status': '200',
                    'msg': 'Success',
                    'activity_id': new_activity_id
                })

        #return res
        
        
    except Exception as e:
        print(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# Update activity record        
@activities_bp.route('/activities/<int:id>', methods=['PUT'])
@login_required
def updateactivity(id):
    conn = None
    cursor = None
    try:
        newrecord = request.get_json()
        name = newrecord['name']

        format = '%Y-%m-%dT%H:%M:%S.%fZ'
        try:
            res = bool(datetime.strptime(newrecord['date'], '%Y-%m-%dT%H:%M:%S.%fZ'))
        except ValueError:
            format = '%Y-%m-%dT%H:%M:%SZ'
        new_format = '%Y-%m-%d %H:%M:%S'
        d = datetime.strptime(newrecord['date'], format)
        #d = dateutil.parser.parse(newrecord['date'])
        nd = d.strftime(new_format)

        sport = newrecord['sport']
        subsport = newrecord['subsport']
        duration = newrecord['duration']
        intensity = newrecord['intensity']
        distance = newrecord['distance']
        avgspeed = newrecord['avgspeed']
        latitude = newrecord['latitude']
        if latitude == '':
            latitude = None
        longitude = newrecord['longitude']
        if longitude == '':
            longitude = None
        equipment = newrecord['equipment']
        if equipment == '':
            equipment = None
        heartrate = newrecord['heartrate']
        if heartrate == '':
            heartrate = 0
        comments = newrecord['comments']
        ascent = newrecord['ascent']
        calories = newrecord['calories']
        avgcadence = newrecord['avgcadence']
        avgpower = newrecord['avgpower']
        device = newrecord['device']
        training_load = newrecord['training_load']
        workout_feel = newrecord['workout_feel']
        workout_rpe = newrecord['workout_rpe']
        ate = newrecord['ate']
        ante = newrecord['ante']
        tzoffset = newrecord['offset']
        if tzoffset == '':
            tzoffset = 0
        hrmfile = newrecord['hrmfile']
        secondhrmfile = newrecord['secondhrmfile']

        # update activity record in database (ensure user owns record)
        user_id = get_user_uuid()
        sqlQuery = "UPDATE activities SET name = %s, date = %s, sport = %s, subsport = %s, duration = %s, intensity = %s, distance = %s, avgspeed = %s, latitude = %s, longitude = %s, equipment = %s, heartrate = %s, comments = %s, ascent = %s, calories = %s, avgcadence = %s, avgpower = %s, device = %s, training_load = %s, workout_feel = %s, workout_rpe = %s, ate = %s, ante = %s, tzoffset = %s, hrmfile = %s, secondhrmfile = %s WHERE id = %s AND user_id = %s"
        # 
        data = (name, nd, sport, subsport, duration, intensity, distance, avgspeed, latitude, longitude, equipment, heartrate, comments, ascent, calories, avgcadence, avgpower, device, training_load, workout_feel, workout_rpe, ate, ante, tzoffset, hrmfile, secondhrmfile, id, user_id)
        #  
        conn = exdb.connect()
        cursor = conn.cursor()
        cursor.execute(sqlQuery, data)
        conn.commit()
        
        res = jsonify('Activity updated successfully.')
        res.status_code = 200

        return res
        
    except Exception as e:
        print(e)
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@activities_bp.route('/activities/bounds', methods=['GET'])
@login_required
def get_activity_bounds():
    # Find the absolute first and last activity dates (for the current user)
    user_id = get_user_uuid()
    query = "SELECT MIN(date), MAX(date) FROM activities WHERE user_id = %s"
    cursor = exdb.get_db().cursor()
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    
    return jsonify({
        "start": result[0], # e.g., "2023-01-15"
        "end": result[1]    # e.g., "2026-03-16"
    })
