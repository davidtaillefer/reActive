import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configuration (read from env, with sensible defaults)
    MYSQL_DATABASE_USER = os.getenv('DB_USER')
    MYSQL_DATABASE_PASSWORD = os.getenv('DB_PASSWORD', os.getenv('MYSQL_DATABASE_PASSWORD'))
    MYSQL_DATABASE_DB = os.getenv('DB_NAME', os.getenv('MYSQL_DATABASE_DB'))
    MYSQL_DATABASE_HOST = os.getenv('DB_HOST', os.getenv('MYSQL_DATABASE_HOST'))
    MYSQL_DATABASE_PORT = int(os.getenv('DB_PORT', os.getenv('MYSQL_DATABASE_PORT')))

    # Flask secret key for sessions
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')

    # Garmins / authentication
    EMAIL = os.getenv('EMAIL')
    PASSWORD = os.getenv('PASSWORD')
    GARMINTOKENS = os.getenv('GARMINTOKENS') or os.path.expanduser('~/.garminconnect')
    GARMINTOKENS_BASE64 = os.getenv('GARMINTOKENS_BASE64') or os.path.expanduser('~/.garminconnect_base64')

    # Base directories - modify these for different deployments
    BASE_DATA_DIR = os.getenv('BASE_DATA_DIR', '/mnt/data')
    BASE_WEB_DIR = os.getenv('BASE_WEB_DIR', '/srv/md0')

    # Equipment paths
    EQUIPMENT_UPLOAD_FOLDER = os.path.join(BASE_DATA_DIR, 'gps', 'images', 'equipment')
    EQUIPMENT_THUMB_FOLDER = os.path.join(EQUIPMENT_UPLOAD_FOLDER, 'thumbs')

    # Activity/HRM paths
    HRM_UPLOAD_FOLDER = os.path.join(BASE_DATA_DIR, 'gps', 'fit')
    LEGACY_HRM_UPLOAD_FOLDER = os.path.join(BASE_WEB_DIR, 'data', 'gps', 'fit')
    EXPORT_DIR = os.path.join(BASE_DATA_DIR, 'gps')
    export_dir = Path(EXPORT_DIR)

    # Runtime helper attributes
    email = EMAIL
    password = PASSWORD
    tokenstore = GARMINTOKENS
    tokenstore_base64 = GARMINTOKENS_BASE64
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    week_start = today - datetime.timedelta(days=7)
    month_start = today - datetime.timedelta(days=30)

    # Training load scaling and smoothing taus
    TRAINING_LOAD_SCALE = float(os.getenv('TRAINING_LOAD_SCALE', '8.49475917047687'))
    TRAINING_ATL_TAU = int(os.getenv('TRAINING_ATL_TAU', '5'))
    TRAINING_CTL_TAU = int(os.getenv('TRAINING_CTL_TAU', '42'))

    # Recipe paths
    RECIPE_UPLOAD_FOLDER = os.path.join(BASE_WEB_DIR, 'www', 'recipes', 'pics')