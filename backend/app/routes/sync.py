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
from flask import Blueprint, jsonify
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
    api_instance = init_api(config.email, config.password)

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
    api_instance = init_api(config.email, config.password)
    if not api_instance:
        return jsonify({'error': 'Failed to initialize API'}), 500

    results = []
    today = date.today()
    
    print("Multi-day sync completed. Now downloading activities...")
    
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
            
            # print(f"Syncing data for: {target_date_str}")
            # print(health_data)
            # print(stats_data)
            
            try:
                # Reuse your existing call_api function
                # This should handle the "Insert on Duplicate Key Update" logic
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
                        date, weight, body_fat, muscle, bone, body_water, bmi, 
                        min_HR, max_HR, resting_HR, avg_SPO2, min_SPO2
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        date, moderate_intensity, vigorous_intensity, intensity_goal, training_status, running_vo2_max, cycling_vo2_max, 
                        total_steps, daily_step_goal, floors_ascended, floors_descended, floor_goal
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    temp_dir = config.export_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
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
        print(f"🔍 Processing activities... {activities}")

        temp_dir = ensure_temp_dir()

        # Download each activity in multiple formats
        for activity in activities:
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
    """Initialize Garmin API with smart error handling and recovery."""
    # First try to login with stored tokens
    try:
        print(f"Attempting to login using stored tokens from: {config.tokenstore}")

        garmin = Garmin()
        garmin.login(config.tokenstore)
        print("Successfully logged in using stored tokens!")
        return garmin

    except (
        FileNotFoundError,
        GarthHTTPError,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
    ):
        print("No valid tokens found. Requesting fresh login credentials.")

    # Loop for credential entry with retry on auth failure
    while True:
        try:
            # Get credentials if not provided
            if not email or not password:
                email = input("Email address: ").strip()
                password = getpass("Password: ")

            print("Logging in with credentials...")
            garmin = Garmin(
                email=email, password=password, is_cn=False, return_on_mfa=True
            )
            result1, result2 = garmin.login()

            if result1 == "needs_mfa":
                print("Multi-factor authentication required")

                mfa_code = get_mfa()
                print("🔄 Submitting MFA code...")

                try:
                    garmin.resume_login(result2, mfa_code)
                    print("✅ MFA authentication successful!")

                except GarthHTTPError as garth_error:
                    # Handle specific HTTP errors from MFA
                    error_str = str(garth_error)
                    print(f"🔍 Debug: MFA error details: {error_str}")

                    if "429" in error_str and "Too Many Requests" in error_str:
                        print("❌ Too many MFA attempts")
                        print("💡 Please wait 30 minutes before trying again")
                        sys.exit(1)
                    elif "401" in error_str or "403" in error_str:
                        print("❌ Invalid MFA code")
                        print("💡 Please verify your MFA code and try again")
                        continue
                    else:
                        # Other HTTP errors - don't retry
                        print(f"❌ MFA authentication failed: {garth_error}")
                        sys.exit(1)

                except GarthException as garth_error:
                    print(f"❌ MFA authentication failed: {garth_error}")
                    print("💡 Please verify your MFA code and try again")
                    continue

            # Save tokens for future use
            garmin.garth.dump(config.tokenstore)
            print(f"Login successful! Tokens saved to: {config.tokenstore}")

            return garmin

        except GarminConnectAuthenticationError:
            print("❌ Authentication failed:")
            print("💡 Please check your username and password and try again")
            # Clear the provided credentials to force re-entry
            email = None
            password = None
            continue

        except (
            FileNotFoundError,
            GarthHTTPError,
            GarthException,
            GarminConnectConnectionError,
            requests.exceptions.HTTPError,
        ) as err:
            print(f"❌ Connection error: {err}")
            print("💡 Please check your internet connection and try again")
            return None

        except KeyboardInterrupt:
            print("\nLogin cancelled by user")
            return None


