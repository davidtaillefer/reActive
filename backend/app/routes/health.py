from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from ..db import exdb
from ..utils import safe_close
from ..utils.user_utils import get_user_uuid
from ..utils.auth import login_required
import pymysql.cursors
import os
from werkzeug.utils import secure_filename

health_records_bp = Blueprint("health_records", __name__)

@health_records_bp.route("/health_records", methods=['GET'])
@login_required
def health_records():
    
    user_id = get_user_uuid()

    try:
        conn = exdb.connect()
        print("Connected to database for health records")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health_records where user_id = %s order by date desc"
        cursor.execute(sql, (user_id,))
        health_records = cursor.fetchall()
        res = jsonify(health_records)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)


@health_records_bp.route('/health_documents/file/<int:doc_id>')
@login_required
def serve_health_document_file(doc_id):
    """Serve the stored file for a health document by its document id."""
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health_record_documents WHERE id = %s"
        cursor.execute(sql, (doc_id,))
        doc = cursor.fetchone()

        if not doc:
            return jsonify({"message": "Document not found"}), 404

        # Ensure the document belongs to the requesting user
        cursor.execute("SELECT user_id FROM health_records WHERE id = %s", (doc.get('health_record_id'),))
        hr = cursor.fetchone()
        user_id = get_user_uuid()
        if not hr or hr.get('user_id') != user_id:
            return jsonify({"message": "Document not found"}), 404

        filename = doc.get('filename')
        if not filename:
            return jsonify({"message": "No filename stored"}), 404

        from flask import current_app, send_from_directory, abort
        import os

        base = current_app.config.get('BASE_DATA_DIR') or os.getenv('BASE_DATA_DIR', '.')
        folder = os.path.join(base, 'health_documents')

        safe_name = os.path.normpath(filename)
        if safe_name.startswith('..') or os.path.isabs(safe_name):
            abort(400)

        full_path = os.path.join(folder, safe_name)
        if not os.path.exists(full_path):
            return jsonify({"message": "File not found on disk"}), 404

        resp = send_from_directory(folder, safe_name)
        resp.cache_control.max_age = 3600
        resp.cache_control.public = True
        return resp
    except Exception as e:
        print(e)
        return jsonify({"message": "Server error"}), 500
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)

@health_records_bp.route("/health_records/<int:record_id>", methods=['GET'])
@login_required
def get_health_record(record_id):
    user_id = get_user_uuid()

    try:
        conn = exdb.connect()
        print("Connected to database for fetching health record")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health_records WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (record_id, user_id))
        record = cursor.fetchone()

        if record:
            res = jsonify(record)
            res.status_code = 200
            return res
        else:
            res = jsonify({"message": "Health record not found"})
            res.status_code = 404
            return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)

@health_records_bp.route("/health_records", methods=['POST'])
@login_required
def add_health_record():
    try:
        newrecord = request.get_json()
        raw = newrecord['date']

        # Handle Z → +00:00 for Python
        raw = raw.replace("Z", "+00:00")

        dt = datetime.fromisoformat(raw)

        # Convert to UTC (important before storing)
        dt_utc = dt  #.astimezone()

        # MySQL DATETIME format
        nd = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
        
        user_id = get_user_uuid()
        date = nd
        type = newrecord.get('type', 'doctor')
        provider = newrecord.get('provider', 'Unknown')
        description = newrecord.get('description', 'No description')

        conn = exdb.connect()
        print("Connected to database for adding health record")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "INSERT INTO health_records (user_id, date, type, provider, description) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (user_id, date, type, provider, description))
        conn.commit()
        res = jsonify({"message": "Health record added"})
        res.status_code = 201

        return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)

@health_records_bp.route("/health_records/<int:record_id>", methods=['PUT'])
@login_required
def update_health_record(record_id):
    try:
        updatedrecord = request.get_json()
        raw = updatedrecord['date']

        # Handle Z → +00:00 for Python
        raw = raw.replace("Z", "+00:00")

        dt = datetime.fromisoformat(raw)

        # Convert to UTC (important before storing)
        dt_utc = dt  #.astimezone()

        # MySQL DATETIME format
        nd = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
        
        user_id = get_user_uuid()
        date = nd
        type = updatedrecord.get('type', 'doctor')
        provider = updatedrecord.get('provider', 'Unknown')
        description = updatedrecord.get('description', 'No description')

        conn = exdb.connect()
        print("Connected to database for updating health record")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "UPDATE health_records SET date = %s, type = %s, provider = %s, description = %s WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (date, type, provider, description, record_id, user_id))
        conn.commit()
        res = jsonify({"message": "Health record updated"})
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)
        
@health_records_bp.route("/health_records/<int:record_id>", methods=['DELETE'])
@login_required
def delete_health_record(record_id):
    user_id = get_user_uuid()

    try:
        conn = exdb.connect()
        print("Connected to database for deleting health record")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "DELETE FROM health_records WHERE id = %s AND user_id = %s"
        cursor.execute(sql, (record_id, user_id))
        conn.commit()
        res = jsonify({"message": "Health record deleted"})
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)

@health_records_bp.route("/health_document/<int:record_id>", methods=['GET'])
@login_required
def get_health_document(record_id):

    try:
        conn = exdb.connect()
        print("Connected to database for fetching health documents")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health_record_documents WHERE id = %s"
        cursor.execute(sql, (record_id,))
        record = cursor.fetchone()

        # Verify ownership via parent health_record
        if record:
            cursor.execute("SELECT user_id FROM health_records WHERE id = %s", (record.get('health_record_id'),))
            hr = cursor.fetchone()
            user_id = get_user_uuid()
            if not hr or hr.get('user_id') != user_id:
                return jsonify({"message": "Health record not found"}), 404

        if record:
            res = jsonify(record)
            res.status_code = 200
            return res
        else:
            res = jsonify({"message": "Health record not found"})
            res.status_code = 404
            return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)

@health_records_bp.route("/health_documents/<int:record_id>", methods=['GET'])
@login_required
def get_health_documents(record_id):

    try:
        conn = exdb.connect()
        print("Connected to database for fetching health documents")
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Verify parent ownership
        cursor.execute("SELECT user_id FROM health_records WHERE id = %s", (record_id,))
        hr = cursor.fetchone()
        user_id = get_user_uuid()
        if not hr or hr.get('user_id') != user_id:
            return jsonify({"message": "Health record not found"}), 404

        sql = "SELECT * FROM health_record_documents WHERE health_record_id = %s"
        cursor.execute(sql, (record_id,))
        record = cursor.fetchall()

        if record:
            res = jsonify(record)
            res.status_code = 200
            return res
        else:
            res = jsonify({"message": "Health record not found"})
            res.status_code = 404
            return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)


@health_records_bp.route('/health_documents/<int:health_record_id>', methods=['POST'])
@login_required
def upload_health_document(health_record_id):
    """Upload a document for a health record. Preserves original filename where possible.
    Expects multipart form-data with field 'file'."""
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'message': 'Invalid filename'}), 400

        base = os.getenv('BASE_DATA_DIR') or current_app.config.get('BASE_DATA_DIR') or '.'
        folder = os.path.join(base, 'health_documents')
        os.makedirs(folder, exist_ok=True)

        # Avoid overwriting existing files while preserving original name where possible
        final_name = filename
        name_root, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(folder, final_name)):
            final_name = f"{name_root}-{counter}{ext}"
            counter += 1

        file_path = os.path.join(folder, final_name)
        file.save(file_path)

        # Verify health record ownership
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT user_id FROM health_records WHERE id = %s", (health_record_id,))
        hr = cursor.fetchone()
        user_id = get_user_uuid()
        if not hr or hr.get('user_id') != user_id:
            return jsonify({'message': 'Health record not found'}), 404

        # Insert metadata into DB
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        sql = "INSERT INTO health_record_documents (health_record_id, filename, created_at, updated_at) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (health_record_id, final_name, now, now))
        conn.commit()
        doc_id = cursor.lastrowid

        # Return the created document record
        cursor.execute("SELECT * FROM health_record_documents WHERE id = %s", (doc_id,))
        doc = cursor.fetchone()
        res = jsonify(doc)
        res.status_code = 201
        return res
    except Exception as e:
        print(e)
        return jsonify({'message': 'Server error'}), 500
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)
