import os
import pymysql
from ..db import exdb
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta

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
        from ..parsers.fit_parser import parse_fit
        from ..services.muscle_service import update_muscle_fatigue
        from ..utils.user_utils import get_user_uuid

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

# GET all activity records 
        
@activities_bp.route('/activities')
def activities():
    try:
        sport = request.args.get('sport')
        startdate = request.args.get('start')
        enddate = request.args.get('end')
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM activities WHERE (%s IS NULL OR sport = %s) AND date BETWEEN %s and %s"
        data = (sport, sport, startdate, enddate)
        cursor.execute(sql, data)
        activities = cursor.fetchall()
        for activity in activities:  
            activity['date'] = activity['date'] + timedelta(hours=activity['tzoffset'])
        res = jsonify(activities)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close() 
        conn.close()

# GET an individual activity by id

@activities_bp.route('/activities/<int:activityid>')
def activity(activityid):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = exdb.get_db().cursor() 
        sql = "SELECT * FROM activities WHERE id=%s"
        cursor.execute(sql, activityid)
        activity = cursor.fetchone()
        res = jsonify(activity)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()

# GET the most recent x activity records 
        
@activities_bp.route('/activities/recent/<int:number>')
def recentactivities(number):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM activities ORDER BY date DESC LIMIT %s"
        cursor.execute(sql, number)
        activities = cursor.fetchall()
        for activity in activities: 
            activity['date'] = activity['date'] + timedelta(hours=activity['tzoffset'])
        res = jsonify(activities)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close() 
        conn.close()

# Create new activity record        
    
@activities_bp.route('/activities', methods=['POST'])
def createactivity():
    print("Received request to create activity with data:", request.get_json())
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
    
        # insert activity record in database
        sqlQuery = "INSERT INTO activities(sport, subsport, date, duration, intensity, distance, avgspeed, latitude, longitude, hrmfile, equipment, heartrate, comments, ascent, calories, avgcadence, avgpower, device, name, training_load, workout_feel, workout_rpe, ate, ante, tzoffset) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        data = (sport, subsport, nd, duration, intensity, distance, avgspeed, latitude, longitude, hrmfile, equipment, heartrate, comments, ascent, calories, avgcadence, avgpower, device, name, training_load, workout_feel, workout_rpe, ate, ante, tzoffset)
        conn = exdb.connect()
        cursor = exdb.get_db().cursor()
        cursor.execute(sqlQuery, data)
        conn.commit()
        new_activity_id = cursor.lastrowid

        # If this is a strength workout with a FIT file, update muscle fatigue
        if sport == STRENGTH_SPORT_ID and hrmfile:
            from ..utils.user_utils import get_user_uuid
            user_id = get_user_uuid()
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
        cursor.close() 
        conn.close()

# Update activity record        
    
@activities_bp.route('/activities/<int:id>', methods=['PUT'])
def updateactivity(id):
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

        # update activity record in database
        sqlQuery = "UPDATE activities SET name = %s, date = %s, sport = %s, subsport = %s, duration = %s, intensity = %s, distance = %s, avgspeed = %s, latitude = %s, longitude = %s, equipment = %s, heartrate = %s, comments = %s, ascent = %s, calories = %s, avgcadence = %s, avgpower = %s, device = %s, training_load = %s, workout_feel = %s, workout_rpe = %s, ate = %s, ante = %s, tzoffset = %s, hrmfile = %s, secondhrmfile = %s WHERE id = %s"
        # 
        data = (name, nd, sport, subsport, duration, intensity, distance, avgspeed, latitude, longitude, equipment, heartrate, comments, ascent, calories, avgcadence, avgpower, device, training_load, workout_feel, workout_rpe, ate, ante, tzoffset, hrmfile, secondhrmfile, id)
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
        cursor.close() 
        conn.close()

@activities_bp.route('/activities/bounds', methods=['GET'])
def get_activity_bounds():
    # Find the absolute first and last activity dates
    query = "SELECT MIN(date), MAX(date) FROM activities"
    cursor = exdb.get_db().cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    
    return jsonify({
        "start": result[0], # e.g., "2023-01-15"
        "end": result[1]    # e.g., "2026-03-16"
    })
