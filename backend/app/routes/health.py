from flask import Blueprint, jsonify

from ..db import exdb
from ..utils import safe_close
from ..utils.user_utils import get_user_uuid
import pymysql.cursors

health_records_bp = Blueprint("health_records", __name__)

@health_records_bp.route("/health_records", methods=['GET'])
def health_records():
    
    user_id = get_user_uuid()

    try:
        conn = exdb.connect()
        print("Connected to database for health records")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health_records"
        cursor.execute(sql)
        health_records = cursor.fetchall()
        res = jsonify(health_records)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)
