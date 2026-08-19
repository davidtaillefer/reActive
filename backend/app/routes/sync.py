import datetime
import io
import json
import logging
import os
import shutil
import sys
import zipfile
from contextlib import suppress
from datetime import timedelta
from getpass import getpass
from io import BytesIO
from pathlib import Path
from typing import Any
from ..db import exdb
import config as app_config
from flask import Blueprint, jsonify, request
from ..utils.auth import login_required
from ..utils.user_utils import get_user_uuid
import uuid
from pymysql import Error
from datetime import timedelta, date

import requests
from garth.exc import GarthException, GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/sync')
def sync():
    # Do not pass global env credentials here — only try per-user tokens.
    api_instance = init_api()

    try:
        if api_instance:
            try:
                response = call_api(api_instance, config.today.isoformat())
            except Exception as e:
                print(
                    f"Unable to fetch stats for display: {e}"
                )  # Silently skip if stats can't be fetched
    except Exception as e:
        print(f"Unexpected error: {e}")
    return jsonify({
                    'res': 'Activity created successfully.',
                    'status': '200',
                    'msg': 'Success'
                })


@sync_bp.route('/sync/days/<int:days>')
def sync_days(days):
    # Use per-user tokens only for scheduled/manual syncs initiated by a user.
    api_instance = init_api()
    if not api_instance:
        return jsonify({'error': 'Failed to initialize API'}), 500

    results = []
    today = date.today()
        
    downloaded_files = []
    try:
        downloaded_files = download_activities_by_date(api_instance)
    except Exception as e:
        print(f"Error downloading activities: {e}")

    try:
        # Loop backwards from today for the specified number of days
        for i in range(days):
            target_date = today - timedelta(days=i)
            target_date_str = target_date.isoformat()
            
            try:
                response = call_api(api_instance, target_date_str)
                results.append({"date": target_date_str, "status": "success"})
            except Exception as e:
                print(f"Error syncing {target_date_str}: {e}")
                results.append({"date": target_date_str, "status": "failed", "error": str(e)})

        return jsonify({
            'res': f'Sync completed for {days} days.',
            'details': results,
            'downloaded_files': downloaded_files,
            'status': '200',
            'msg': 'Success'
        })

    except Exception as e:
        print(f"Unexpected error during multi-day sync: {e}")
        return jsonify({'error': str(e)}), 500
    
        

# Configure logging to reduce verbose error output from garminconnect library
# This prevents double error messages for known API issues
logging.getLogger("garminconnect").setLevel(logging.CRITICAL)

api: Garmin | None = None

# In-memory store for active MFA login sessions.
# Keyed by resume_id (uuid4 string) => {"garmin": Garmin instance, "resume_data": obj}
mfa_sessions: dict[str, dict] = {}


@sync_bp.route('/sync/credentials/status', methods=['GET'])
@login_required
def credentials_status():
    """Return whether stored tokens or env credentials are available.

    Only per-user token files are considered valid for user-initiated syncs.
    This endpoint also returns the Garmin profile id extracted from the
    token (if available) and the stored profile id for the app user so the
    frontend can determine whether the token belongs to the correct account.
    """

    status = {
        "has_tokens": False,
        "has_env_credentials": False,
        "tokens_garmin_id": None,
        "stored_garmin_id": None,
        "is_owner_match": False,
    }

    user_id = get_user_uuid()

    # Check for per-user token file and read its profile if present
    try:
        token_path = None
        if user_id and getattr(config, 'tokenstore', None):
            token_path = os.path.expanduser(config.tokenstore) + f'.{user_id}'

        if token_path and os.path.exists(token_path):
            try:
                garmin = Garmin()
                garmin.login(token_path)
                status["has_tokens"] = True
                try:
                    profile = garmin.get_user_profile() or {}
                    tokens_garmin_id = profile.get('id')
                    if tokens_garmin_id is not None:
                        try:
                            tokens_garmin_id = int(tokens_garmin_id)
                        except Exception:
                            pass
                    status['tokens_garmin_id'] = tokens_garmin_id
                except Exception:
                    status['tokens_garmin_id'] = None
            except Exception:
                status["has_tokens"] = False
        else:
            status["has_tokens"] = False
    except Exception:
        status["has_tokens"] = False

    # Check for environment-provided credentials (informational only)
    if config.email and config.password:
        status["has_env_credentials"] = True

    # Load stored Garmin id for this app user and compare
    try:
        if user_id:
            stored_garmin_id = _get_stored_garmin_id(user_id)
            status['stored_garmin_id'] = stored_garmin_id
            status['is_owner_match'] = (
                status.get('tokens_garmin_id') is not None
                and stored_garmin_id is not None
                and str(status.get('tokens_garmin_id')) == str(stored_garmin_id)
            )
    except Exception:
        status['stored_garmin_id'] = None
        status['is_owner_match'] = False

    return jsonify(status)


def _ensure_garmin_accounts_table():
    """Create a minimal `garmin_accounts` table if it doesn't exist."""
    try:
        conn = exdb.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_accounts (
                user_id INT PRIMARY KEY,
                garmin_id INT(11),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        conn.commit()
    except Exception:
        pass
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


def _upsert_garmin_account(user_id: int, garmin_id: int | None):
    _ensure_garmin_accounts_table()
    try:
        conn = exdb.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO garmin_accounts (user_id, garmin_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE garmin_id=VALUES(garmin_id), updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, garmin_id),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


def _get_stored_garmin_id(user_id: int):
    try:
        conn = exdb.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT garmin_id FROM garmin_accounts WHERE user_id=%s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return row[0]
    except Exception:
        return None
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@sync_bp.route('/sync/credentials', methods=['POST'])
@login_required
def credentials_login():
    """Accept email/password JSON and attempt a non-interactive login.

    If MFA is required, returns 202 with a `resume_id` to be used with
    `/sync/credentials/mfa`.
    """
    payload = request.get_json(force=True)
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    try:
        garmin = Garmin(email=email, password=password, is_cn=False, return_on_mfa=True)
        result1, result2 = garmin.login()

        if result1 == "needs_mfa":
            resume_id = str(uuid.uuid4())
            mfa_sessions[resume_id] = {"garmin": garmin, "resume_data": result2}
            return jsonify({"mfa_required": True, "resume_id": resume_id}), 202

        # Successful login — save tokens per-user
        user_id = get_user_uuid()
        garmin_id = None
        token_path = None
        if getattr(config, 'tokenstore', None):
            token_path = os.path.expanduser(config.tokenstore) + f'.{user_id}'
        # ensure parent dir exists
        if token_path:
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            garmin.garth.dump(token_path)
            try:
                profile = garmin.get_user_profile() or {}
                garmin_id = profile.get('id')
                if garmin_id is not None:
                    try:
                        garmin_id = int(garmin_id)
                    except Exception:
                        pass
                if user_id:
                    _upsert_garmin_account(user_id, garmin_id)
            except Exception:
                pass
        # Return Garmin id so frontend can update its UI immediately
        return jsonify({"mfa_required": False, "message": "Login successful", "garmin_id": garmin_id}), 200

    except GarminConnectAuthenticationError as e:
        return jsonify({"error": "Authentication failed", "detail": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Login error", "detail": str(e)}), 500


@sync_bp.route('/sync/credentials/mfa', methods=['POST'])
@login_required
def credentials_mfa():
    """Submit MFA code for an in-progress login identified by `resume_id`."""
    payload = request.get_json(force=True)
    resume_id = payload.get("resume_id")
    code = payload.get("code")

    if not resume_id or not code:
        return jsonify({"error": "resume_id and code required"}), 400

    session = mfa_sessions.get(resume_id)
    if not session:
        return jsonify({"error": "Invalid resume_id"}), 404

    garmin = session.get("garmin")
    resume_data = session.get("resume_data")

    try:
        garmin.resume_login(resume_data, code)
        # Save tokens per-user
        user_id = get_user_uuid()
        garmin_id = None
        token_path = None
        if getattr(config, 'tokenstore', None):
            token_path = os.path.expanduser(config.tokenstore) + f'.{user_id}'
        if token_path:
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            garmin.garth.dump(token_path)
            try:
                profile = garmin.get_user_profile() or {}
                garmin_id = profile.get('id')
                if garmin_id is not None:
                    try:
                        garmin_id = int(garmin_id)
                    except Exception:
                        pass
                if user_id:
                    _upsert_garmin_account(user_id, garmin_id)
            except Exception:
                pass
        # Clean up session
        del mfa_sessions[resume_id]
        # Return Garmin id so frontend can update its UI immediately
        return jsonify({"message": "MFA succeeded, tokens saved", "garmin_id": garmin_id}), 200

    except GarthHTTPError as garth_error:
        return jsonify({"error": "MFA failed", "detail": str(garth_error)}), 400
    except Exception as e:
        return jsonify({"error": "MFA error", "detail": str(e)}), 500


@sync_bp.route('/sync/credentials/logout', methods=['POST'])
@login_required
def credentials_logout():
    """Remove stored Garmin token files from disk."""
    removed = []
    errors = []
    user_id = get_user_uuid()
    paths = []
    if getattr(config, 'tokenstore', None):
        paths.append(os.path.expanduser(config.tokenstore) + f'.{user_id}')
    if getattr(config, 'tokenstore_base64', None):
        paths.append(os.path.expanduser(config.tokenstore_base64) + f'.{user_id}')

    for p in paths:
        if not p:
            continue
        try:
            if os.path.exists(p):
                os.remove(p)
                removed.append(p)
        except Exception as e:
            errors.append({"path": p, "error": str(e)})

    # clear in-memory MFA sessions too
    mfa_sessions.clear()

    return jsonify({"removed": removed, "errors": errors}), 200



# Initialize configuration using the shared app config module
config = app_config.Config()

health_data = {
    "date": '',
    "weight": 0,
    "body_fat": 0,
    "muscle": 0,
    "bone": 0,
    "body_water": 0,
    "bmi": 0,
    "min_hr": 0,
    "max_hr": 0,
    "resting_hr": 0,
    "avg_SPO2": 0,
    "min_SPO2": 0,
}

stats_data = {
    "date": '',
    "moderate_intensity": 0,
    "vigorous_intensity": 0,
    "intensity_goal": 0,
    "training_status": 0,
    "running_vo2_max": 0,
    "cycling_vo2_max": 0,
    "total_steps": 0,
    "daily_step_goal": 0,
    "floors_ascended": 0,
    "floors_descended": 0,
    "floor_goal": 0,
    "training_status": 0
}

def get_mfa() -> str:
    """Get MFA token."""
    return input("MFA one-time code: ")


# Call Garmin API and procees incoming data

def call_api(api, date):

    try:
        user_id = get_user_uuid()

        stats = api.get_stats_and_body(date)
        training = api.get_training_status(date)

        if stats:
            health_data["date"] = stats.get("calendarDate")
            health_data["min_hr"] = stats.get("minHeartRate")
            health_data["max_hr"] = stats.get("maxHeartRate")
            health_data["resting_hr"] = stats.get("restingHeartRate")
            health_data["weight"] = stats.get("weight")
            health_data["bmi"] = stats.get("bmi")
            health_data["body_fat"] = stats.get("bodyFat")
            health_data["body_water"] = stats.get("bodyWater")
            health_data["bone"] = stats.get("boneMass")
            health_data["muscle"] = stats.get("muscleMass")
            health_data["avg_SPO2"] = stats.get("averageSpo2")
            health_data["min_SPO2"] = stats.get("lowestSpo2")

            stats_data["date"] = date
            stats_data["moderate_intensity"] = stats.get("moderateIntensityMinutes")
            stats_data["vigorous_intensity"] = stats.get("vigorousIntensityMinutes")

            stats_data["intensity_goal"] = stats.get("intensityMinutesGoal")

            stats_data["total_steps"] = stats.get("totalSteps")
            stats_data["daily_step_goal"] = stats.get("dailyStepGoal")

            stats_data["floors_ascended"] = stats.get("floorsAscended")
            stats_data["floors_descended"] = stats.get("floorsDescended")
            stats_data["floor_goal"] = stats.get("userFloorsAscendedGoal")

            stats_data["running_vo2_max"] = training.get("mostRecentVO2Max", {}).get("generic", {}).get("vo2MaxPreciseValue", "Not Found")
            #   
            level_3 = training.get("mostRecentTrainingStatus", {}).get("latestTrainingStatusData", {})
            target_obj = next(iter(level_3.values()), {})
            stats_data["training_status"] = target_obj.get("trainingStatus")


            formatted_output = json.dumps(target_obj, indent=2, default=str)
            #formatted_output = json.dumps(training, indent=2, default=str)
            #print(formatted_output)

            try:
                sqlQuery = """
                    INSERT INTO health (
                        user_id, date, weight, body_fat, muscle, bone, body_water, bmi, 
                        min_HR, max_HR, resting_HR, avg_SPO2, min_SPO2
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        weight = VALUES(weight), 
                        body_fat = VALUES(body_fat),
                        muscle = VALUES(muscle),
                        bone = VALUES(bone),
                        body_water = VALUES(body_water),
                        bmi = VALUES(bmi),
                        min_HR = VALUES(min_HR),
                        max_HR = VALUES(max_HR),
                        resting_HR = VALUES(resting_HR),
                        avg_SPO2 = VALUES(avg_SPO2),
                        min_SPO2 = VALUES(min_SPO2)
                """

                data = (
                    user_id,
                    health_data["date"], 
                    health_data.get("weight"), 
                    health_data.get("body_fat"), 
                    health_data.get("muscle"), 
                    health_data.get("bone"), 
                    health_data.get("body_water"), 
                    health_data.get("bmi"), 
                    health_data.get("min_hr"), 
                    health_data.get("max_hr"), 
                    health_data.get("resting_hr"), 
                    health_data.get("avg_SPO2"), 
                    health_data.get("min_SPO2")
                )

                conn = exdb.connect()
                cursor = conn.cursor() 
                cursor.execute(sqlQuery, data)
                conn.commit()
                print("Health record saved successfully!")

            except Exception as e:
                print(f"DATABASE ERROR: {e}")
                return {"error": str(e)}, 400 
            finally:
                if 'conn' in locals():
                    conn.close()
            try:
                sqlQuery = """
                    INSERT INTO stats (
                        user_id, date, moderate_intensity, vigorous_intensity, intensity_goal, training_status, running_vo2_max, cycling_vo2_max, 
                        total_steps, daily_step_goal, floors_ascended, floors_descended, floor_goal
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        moderate_intensity = VALUES(moderate_intensity), 
                        vigorous_intensity = VALUES(vigorous_intensity),
                        intensity_goal = VALUES(intensity_goal),
                        training_status = VALUES(training_status),
                        running_vo2_max = VALUES(running_vo2_max),
                        cycling_vo2_max = VALUES(cycling_vo2_max),
                        total_steps = VALUES(total_steps),
                        daily_step_goal = VALUES(daily_step_goal),
                        floors_ascended = VALUES(floors_ascended),
                        floors_descended = VALUES(floors_descended),
                        floor_goal = VALUES(floor_goal)
                """

                data = (
                    user_id,
                    stats_data["date"], 
                    stats_data.get("moderate_intensity"), 
                    stats_data.get("vigorous_intensity"), 
                    stats_data.get("intensity_goal"), 
                    stats_data.get("training_status"), 
                    stats_data.get("running_vo2_max"), 
                    stats_data.get("cycling_vo2_max"), 
                    stats_data.get("total_steps"), 
                    stats_data.get("daily_step_goal"), 
                    stats_data.get("floors_ascended"), 
                    stats_data.get("floors_descended"), 
                    stats_data.get("floor_goal")
                )

                conn = exdb.connect()
                cursor = conn.cursor() 
                cursor.execute(sqlQuery, data)
                conn.commit()
                print("Stats record saved successfully!")

            except Exception as e:
                print(f"DATABASE ERROR: {e}")
                return {"error": str(e)}, 400 
            finally:
                if 'conn' in locals():
                    conn.close()
        return True

    except GarthHTTPError as e:
        # Handle specific HTTP errors more gracefully
        error_str = str(e)

        # Extract status code more reliably
        status_code = None
        if hasattr(e, "response") and hasattr(e.response, "status_code"):
            status_code = e.response.status_code

        # Handle specific status codes
        if status_code == 400 or ("400" in error_str and "Bad Request" in error_str):
            error_msg = "Endpoint not available (400 Bad Request) - This feature may not be enabled for your account or region"
            # Don't print for 400 errors as they're often expected for unavailable features
        elif status_code == 401 or "401" in error_str:
            error_msg = (
                "Authentication required (401 Unauthorized) - Please re-authenticate"
            )
            print(f"⚠️ failed: {error_msg}")
        elif status_code == 403 or "403" in error_str:
            error_msg = "Access denied (403 Forbidden) - Your account may not have permission for this feature"
            print(f"⚠️ failed: {error_msg}")
        elif status_code == 404 or "404" in error_str:
            error_msg = (
                "Endpoint not found (404) - This feature may have been moved or removed"
            )
            print(f"⚠️ failed: {error_msg}")
        elif status_code == 429 or "429" in error_str:
            error_msg = (
                "Rate limit exceeded (429) - Please wait before making more requests"
            )
            print(f"⚠️ failed: {error_msg}")
        elif status_code == 500 or "500" in error_str:
            error_msg = "Server error (500) - Garmin's servers are experiencing issues"
            print(f"⚠️ failed: {error_msg}")
        elif status_code == 503 or "503" in error_str:
            error_msg = "Service unavailable (503) - Garmin's servers are temporarily unavailable"
            print(f"⚠️ failed: {error_msg}")
        else:
            error_msg = f"HTTP error: {e}"

        print(f"⚠️ failed: {error_msg}")
        return False, error_msg

    except GarminConnectAuthenticationError as e:
        error_msg = f"Authentication issue: {e}"
        print(f"⚠️ failed: {error_msg}")
        return False, error_msg

    except GarminConnectConnectionError as e:
        error_msg = f"Connection issue: {e}"
        print(f"⚠️ failed: {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        exc_type, exc_obj, exc_tb = sys.exc_info()
        line_number = exc_tb.tb_lineno
        print(f"⚠️ failed: {error_msg} at line {line_number}")
        return False, error_msg

def format_timedelta(td):
    minutes, seconds = divmod(td.seconds + td.days * 86400, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}"


def download_activities_by_date(api: Garmin) -> None:
    """Download activities by date range."""
    try:
        print(
            f"📥 Downloading activities by date range ({config.week_start.isoformat()} to {date.today.isoformat()})..."
        )

        # Get activities for the date range (last 7 days as default)
        activities = api.get_activities_by_date(
            config.week_start.isoformat(), date.today.isoformat()
        )

        if not activities:
            print("ℹ️ No activities found in the specified date range")
            return

        print(f"📊 Found {len(activities)} activities to download")
        # print(f"🔍 Processing activities... {activities}")

        # Download each activity in multiple formats
        for activity in activities:
            activity_id = activity.get("activityId")
            activity_name = activity.get("activityName", "Unknown")
            start_time_local = activity.get("startTimeLocal", "").replace(":", "-")
            start_time = activity.get("startTimeGMT", "").replace(":", "-")

            if not activity_id:
                continue

            print(f"📥 Downloading: {activity_name} (ID: {activity_id}) date: {start_time}")

            fmt = "ORIGINAL"

            try:
                filename = f"{start_time}_{activity_id}_ACTIVITY.{fmt.lower()}"
                if fmt == "ORIGINAL":
                    filename = f"{start_time}_{activity_id}_ACTIVITY.zip"

                filepath = config.export_dir / filename

                # Download the file from Garmin using proper enum values
                dl_fmt = api.ActivityDownloadFormat.ORIGINAL

                content = api.download_activity(activity_id, dl_fmt=dl_fmt)

                if content:
                    with open(filepath, "wb") as f:
                        f.write(content)
                    print(f"  ✅ {fmt}: {filename}")
                else:
                    print(f"  ❌ {fmt}: No content available")

            except Exception as e:
                print(f"  ❌ {fmt}: Error downloading - {e}")

        print(f"✅ Activity downloads completed! Files saved to: {config.export_dir}")
        return downloaded_files

    except Exception as e:
        print(f"❌ Error downloading activities: {e}")
        return downloaded_files


def parse_garmin_datetime(datetime_str: str) -> datetime.datetime | None:
    if not datetime_str:
        return None

    normalized = datetime_str.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            return None


def activity_exists(start_time: datetime.datetime) -> bool:
    if not start_time:
        return False

    query = "SELECT 1 FROM activities WHERE date = %s LIMIT 1"
    params = (start_time.strftime('%Y-%m-%d %H:%M:%S'),)
    try:
        conn = exdb.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        exists = cursor.fetchone() is not None
        return exists
    except Exception as e:
        print(f"Error checking activity existence: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


def ensure_temp_dir() -> Path:
    print(f"📂 Ensuring temporary directory exists at: {config.export_dir / 'temp'}")
    temp_dir = config.export_dir / "temp"
    print(f"📂 Temporary directory path: {temp_dir}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    print("✅ Temporary directory is ready.")
    return temp_dir


def extract_activity_file(zip_path: Path, temp_dir: Path) -> Path | None:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            candidates = [name for name in zf.namelist() if Path(name).suffix.lower() in {'.fit', '.tcx', '.gpx'}]
            if not candidates:
                print(f"No extractable activity file found in {zip_path}")
                return None

            selected = candidates[0]
            extracted_path = temp_dir / Path(selected).name
            with zf.open(selected) as source, open(extracted_path, 'wb') as target:
                target.write(source.read())
            return extracted_path
    except Exception as e:
        print(f"Error extracting activity file from zip {zip_path}: {e}")
        return None


def move_activity_file(extracted_path: Path) -> Path | None:
    suffix = extracted_path.suffix.lower()
    if suffix not in {'.fit', '.tcx', '.gpx'}:
        print(f"Unsupported activity file type: {suffix}")
        return None

    destination_folder = config.export_dir / suffix.lstrip('.')
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination_path = destination_folder / extracted_path.name

    try:
        shutil.move(str(extracted_path), destination_path)
        return destination_path
    except Exception as e:
        print(f"Error moving file {extracted_path} to {destination_path}: {e}")
        return None


def cleanup_zip(zip_path: Path) -> None:
    with suppress(Exception):
        zip_path.unlink()


def save_temp_zip(activity_id: Any, start_time: str, content: bytes, temp_dir: Path) -> Path:
    zip_filename = f"{start_time}_{activity_id}_ACTIVITY.zip"
    zip_path = temp_dir / zip_filename
    with open(zip_path, 'wb') as f:
        f.write(content)
    return zip_path


def download_activities_by_date(api: Garmin) -> list[str]:
    """Download activities by date range."""
    downloaded_files: list[str] = []
    try:
        print(
            f"📥 Downloading activities by date range ({config.week_start.isoformat()} to {config.today.isoformat()})..."
        )

        # Get activities for the date range (last 7 days as default)
        activities = api.get_activities_by_date(
            config.week_start.isoformat(), config.today.isoformat()
        )

        if not activities:
            print("ℹ️ No activities found in the specified date range")
            return downloaded_files

        print(f"📊 Found {len(activities)} activities to download")

        temp_dir = ensure_temp_dir()
        print(f"📂 Temporary directory for downloads: {temp_dir}")
        

        # Download each activity in multiple formats
        for activity in activities:
            print(f"🔍 Processing activity: {activity.get('activityName', 'Unknown')}")

            activity_id = activity.get("activityId")
            activity_name = activity.get("activityName", "Unknown")
            start_time_str = activity.get("startTimeGMT", "")
            start_time = start_time_str.replace(":", "-")

            if not activity_id or not start_time_str:
                continue

            parsed_start_time = parse_garmin_datetime(start_time_str)
            if activity_exists(parsed_start_time):
                print(f"⏭️ Skipping already stored activity: {activity_name} (ID: {activity_id})")
                continue

            print(f"📥 Downloading: {activity_name} (ID: {activity_id}) date: {start_time_str}")

            try:
                content = api.download_activity(activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL)
                if not content:
                    print(f"  ❌ ORIGINAL: No content available")
                    continue

                zip_path = save_temp_zip(activity_id, start_time, content, temp_dir)
                extracted_path = extract_activity_file(zip_path, temp_dir)
                if not extracted_path:
                    cleanup_zip(zip_path)
                    continue

                moved_path = move_activity_file(extracted_path)
                cleanup_zip(zip_path)

                if moved_path:
                    downloaded_files.append(str(moved_path.name))
                    print(f"  ✅ Saved activity file to {moved_path}")
                else:
                    print(f"  ❌ Failed to move extracted file for {activity_name}")

            except Exception as e:
                print(f"  ❌ Error downloading activity {activity_name}: {e}")

        print(f"✅ Activity downloads completed! Files saved to: {config.export_dir}")
        return downloaded_files

    except Exception as e:
        print(f"❌ Error downloading activities: {e}")
        return downloaded_files


def remove_stored_tokens():
    """Remove stored login tokens."""
    try:
        import os
        import shutil

        token_path = os.path.expanduser(config.tokenstore)
        if os.path.isdir(token_path):
            shutil.rmtree(token_path)
            print("✅ Stored login tokens directory removed")
        else:
            print("ℹ️ No stored login tokens found")
    except Exception as e:
        print(f"❌ Error removing stored login tokens: {e}")


def disconnect_api(api: Garmin):
    """Disconnect from Garmin Connect."""
    api.logout()
    print("✅ Disconnected from Garmin Connect")


def init_api(email: str | None = None, password: str | None = None) -> Garmin | None:
    """Initialize Garmin API non-interactively.

    This function will first try stored tokens. If no valid tokens are present
    it will return None unless `email` and `password` are provided, in which
    case it will attempt to log in and may return a Garmin instance or None on
    failure.
    """
    # Try to login with stored tokens (per-user only). We intentionally
    # do NOT fall back to a global tokenstore here — doing so can cause
    # one user's actions to run under another user's Garmin account.
    try:
        user_id = get_user_uuid()
        if user_id and getattr(config, 'tokenstore', None):
            per_user_token = os.path.expanduser(config.tokenstore) + f'.{user_id}'
            try:
                print(f"Attempting to login using per-user stored tokens from: {per_user_token}")
                garmin = Garmin()
                garmin.login(per_user_token)
                print("Successfully logged in using per-user stored tokens!")
                return garmin
            except Exception:
                print("Per-user tokens not valid or not present; not using global tokens for security")
        else:
            print("No per-user tokenstore configured for this request")

    except (
        FileNotFoundError,
        GarthHTTPError,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
    ):
        print("No valid per-user tokens found.")

    # If no credentials were provided, do not prompt interactively in containerized
    # environments — return None and let the HTTP endpoints drive the login flow.
    if not email or not password:
        print("No credentials provided; returning None (credentials required)")
        return None

    # If credentials are provided, attempt non-interactive login and signal MFA
    try:
        print("Logging in with provided credentials...")
        garmin = Garmin(email=email, password=password, is_cn=False, return_on_mfa=True)
        result1, result2 = garmin.login()

        if result1 == "needs_mfa":
            # Caller should handle MFA via the /sync/credentials and
            # /sync/credentials/mfa HTTP endpoints. Return None here so
            # calling code knows no active API instance is available.
            print("MFA required for provided credentials")
            return None

        # Save tokens and return the instance
        # Prefer saving tokens to a per-user tokenstore so env/admin creds
        # don't become global tokens that other users will inherit.
        user_id = None
        try:
            user_id = get_user_uuid()
        except Exception:
            user_id = None

        if user_id and getattr(config, 'tokenstore', None):
            target = os.path.expanduser(config.tokenstore) + f'.{user_id}'
        else:
            # Fallback to global tokenstore if no user context
            target = config.tokenstore

        os.makedirs(os.path.dirname(os.path.expanduser(target)), exist_ok=True)
        garmin.garth.dump(target)
        print(f"Login successful! Tokens saved to: {target}")
        return garmin

    except GarminConnectAuthenticationError:
        print("Authentication failed for provided credentials")
        return None

    except (
        FileNotFoundError,
        GarthHTTPError,
        GarthException,
        GarminConnectConnectionError,
        requests.exceptions.HTTPError,
    ) as err:
        print(f"Connection error: {err}")
        return None


