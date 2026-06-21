import traceback
from urllib import response
import uuid

import pymysql
import os
import json
import xmltodict
from ..db import exdb
from flask import (
    Blueprint,
    jsonify,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
    abort,
    current_app,
)
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import re
from garmin_fit_sdk import Decoder, Stream
import math
import numbers
import time
import pymysql
from PIL import Image
from ..utils import safe_close


main_bp = Blueprint("main", __name__)

def get_equipment_upload_folder():
    return current_app.config["EQUIPMENT_UPLOAD_FOLDER"]

def get_equipment_thumb_folder():
    return current_app.config["EQUIPMENT_THUMB_FOLDER"]


def get_hrm_upload_folder():
    return current_app.config["HRM_UPLOAD_FOLDER"]


def get_recipe_upload_folder():
    return current_app.config["RECIPE_UPLOAD_FOLDER"]


# Upload picture


@main_bp.route("/upload", methods=["POST"])
def uploadpicture():

    UPLOAD_FOLDER = get_recipe_upload_folder()
    ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
    try:
        # newrecord = request.get_json()
        # print(newrecord)

        if request.method == "POST":
            if "file" not in request.files:
                flash("No file part")
                return redirect(request.url)
                # f = request.form['file']
                file = request.files["file"]
            # filenum = f.filenum
            for key in file:
                print(key)
            # print(file)
            if file.filename == "":
                flash("No selected file")
                print("No selected file")
                return redirect(request.url)
            if file and allowed_file(file.filename):
                print("File allowed")
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                return redirect(url_for("download_file", name=filename))
            # print(f.items())
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # f.save(os.path.join('/srv/md0/www/recipes/pics', filenum))

        return jsonify(
            {
                "res": "Photo uploaded successfully.",
                "status": "200",
                "msg": "Success",
                "no_of_books": 10,
            }
        )

    except Exception as e:
        print(e)
    finally:
        print("Picture Upload Done!")


# Upload hrm file


@main_bp.route("/uploadhrm2", methods=["POST"])
def uploadhrm2():

    UPLOAD_FOLDER = get_hrm_upload_folder()
    ALLOWED_EXTENSIONS = {"fit", "tcx", "gpx"}
    print("Request received for HRM upload")

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    try:
        if request.method == "POST":
            file = request.files["file"]
            if file.filename == "":
                print("No selected file")
                return redirect(request.url)
            if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
                print("File allowed")
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                return jsonify(
                    {
                        "res": "HRM File Sucessfully Uploaded.",
                        "status": "200",
                        "filename": filename,
                        "msg": "Success",
                    }
                )
            return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@main_bp.route("/uploadhrm", methods=["POST"])
def uploadhrm():

    UPLOAD_FOLDER = get_hrm_upload_folder()

    if "file" not in request.files:
        return "No file part in the request", 400

    file = request.files["file"]

    if file.filename == "":
        return "No file selected", 400

    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    return "File uploaded successfully"


# GET all sport records


@main_bp.route("/sports")
def sports():
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = exdb.get_db().cursor()
        sql = "SELECT * FROM sports ORDER BY name"
        # sql = "SHOW TABLES"
        cursor.execute(sql)
        sports = cursor.fetchall()
        res = jsonify(sports)
        res.status_code = 200

        return res
    except Exception as e:
        print("Error fetching sports: ", e)
    finally:
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass


# GET a subsport based on passed sport


@main_bp.route("/subsport/<int:sportid>")
def subsports(sportid):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = exdb.get_db().cursor()
        sql = "SELECT * FROM subsport WHERE sportid=%s"
        # sql = "SHOW TABLES"
        cursor.execute(sql, sportid)
        subsports = cursor.fetchall()
        res = jsonify(subsports)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        safe_close(cursor if 'cursor' in locals() else None, conn if 'conn' in locals() else None)


# validation.py


def equipment_schema():
    return {
        "idk": {"type": int, "required": False},
        "name": {"type": str, "required": True},
        "sportid": {"type": int, "required": False},
        "brand": {"type": str, "required": False},
        "model": {"type": str, "required": False},
        "year": {"type": int, "required": False, "min": 1900, "max": 2100},
        "life_span": {"type": float, "required": False, "min": 0},
        "maintenance_notes": {"type": str, "required": False},
    }


# validation.py


def validate_form(data, schema):
    errors = {}
    cleaned = {}

    for field, rules in schema.items():
        raw_value = data.get(field)

        # --- Required check ---
        if rules.get("required") and not raw_value:
            errors[field] = "This field is required"
            continue

        # Skip empty optional fields
        if not raw_value:
            cleaned[field] = None
            continue

        # --- Type conversion ---
        try:
            if rules["type"] == int:
                value = int(raw_value)
            elif rules["type"] == float:
                value = float(raw_value)
            elif rules["type"] == str:
                value = str(raw_value).strip()
            else:
                value = raw_value
        except ValueError:
            errors[field] = f"Invalid {rules['type'].__name__}"
            continue

        # --- Min / Max ---
        if "min" in rules and value is not None and value < rules["min"]:
            errors[field] = f"Must be ≥ {rules['min']}"
            continue

        if "max" in rules and value is not None and value > rules["max"]:
            errors[field] = f"Must be ≤ {rules['max']}"
            continue

        cleaned[field] = value

    return cleaned, errors

def delete_image(filename):
    main = os.path.join(get_equipment_upload_folder(), filename)
    thumb = os.path.join(get_equipment_thumb_folder(), filename)

    for path in (main, thumb):
        if os.path.exists(path):
            os.remove(path)

def process_image(file):
    ext = file.filename.rsplit('.', 1)[-1].lower()
    filename = f"{uuid.uuid4()}.jpg"  # force jpg for compression

    filepath = os.path.join(get_equipment_upload_folder(), filename)
    thumbpath = os.path.join(get_equipment_thumb_folder(), filename)

    img = Image.open(file).convert('RGB')

    # --- Main image ---
    max_size = (1200, 1200)
    img.thumbnail(max_size)

    img.save(filepath, format='JPEG', quality=80, optimize=True)

    # --- Thumbnail ---
    thumb = Image.open(filepath)
    thumb.thumbnail((300, 300))

    thumb.save(thumbpath, format='JPEG', quality=75, optimize=True)

    return filename


@main_bp.route("/equipment/<int:eqid>")
def equipment(eqid):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = exdb.get_db().cursor()
        sql = "SELECT * FROM equipment WHERE sportid=%s"
        # sql = "SHOW TABLES"
        cursor.execute(sql, eqid)
        equipment = cursor.fetchall()
        res = jsonify(equipment)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()


@main_bp.route("/equipment2/<int:eqid>")
def equipment2(eqid):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # cursor = exdb.get_db().cursor()
        sql = "SELECT * FROM equipment WHERE idk=%s"
        # sql = "SHOW TABLES"
        cursor.execute(sql, eqid)
        equipment = cursor.fetchall()
        res = jsonify(equipment)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()

# GET the total distance for an equipment by id 
        
@main_bp.route('/equipment/usage/<int:number>')
def equipmentusage(number):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT COALESCE(SUM(distance), 0) AS total_distance FROM activities WHERE equipment = %s;"
        cursor.execute(sql, (number,))
        total = cursor.fetchone()
        res = jsonify(total)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close() 
        conn.close()

# CREATE equipment record

@main_bp.route("/equipment", methods=["POST"])
def createequipment():
    import os
    from werkzeug.utils import secure_filename

    UPLOAD_FOLDER = get_equipment_upload_folder()

    file = request.files.get("photo")
    filename = None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(get_equipment_thumb_folder(), exist_ok=True)

    if file:
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            return jsonify({"errors": {"photo": "Invalid file type"}}), 400

    try:
        if file:
            filename = process_image(file)
            filename = secure_filename(filename)

            print(f"Saved file to {UPLOAD_FOLDER}/{filename}")

        form_data = request.form

        cleaned, errors = validate_form(form_data, equipment_schema())

        if errors:
            return jsonify({"errors": errors}), 400

        # idk = float(cleaned.get("idk")) if cleaned.get("idk") else None
        # name = cleaned.get("name")
        # sport_id = str(cleaned.get("sportid"))
        # brand = cleaned.get("brand") if cleaned.get("brand") else ""
        # model = cleaned.get("model") if cleaned.get("model") else ""
        # year = str(cleaned.get("year")) if cleaned.get("year") else ""
        # life_span = cleaned.get("life_span") if cleaned.get("life_span") else ""
        # maintenance_notes = cleaned.get("maintenance_notes") if cleaned.get("maintenance_notes") else ""
        # photo = filename
        
        sport_id  = form_data.get("sportid")
        name = form_data.get("name")
        brand = form_data.get("brand", "")
        model = form_data.get("model", "")
        year = form_data.get("year", "")
        life_span = form_data.get("life_span", "")
        maintenance_notes = form_data.get("maintenance_notes", "")  
        

        print("FORM:", request.form)
        print("FILES:", request.files)

        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        if filename:
            print("Inserting with photo")
            sqlQuery = "INSERT INTO equipment(id, sportid, name, brand, model, year, life_span, maintenance_notes, photo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            data = ('0', sport_id, name, brand, model, year, life_span, maintenance_notes, filename)
            print("data: ", data)
            cursor.execute(sqlQuery, data)
        else:
            cursor.execute(
                """
                INSERT INTO equipment (name, sportid, id, brand, model, year, life_span, maintenance_notes, photo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (name, sport_id, '0', brand, model, year, life_span, maintenance_notes, filename),
            )

        conn.commit()

        return {"status": "ok"}

    except Exception as e:
        traceback.print_exc()   # 🔥 THIS is key
        return {"error": str(e)}, 500
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
        
# Update equipment record

@main_bp.route("/equipment/<int:id>", methods=["PUT"])
def updateequipment(id):
    import os
    from werkzeug.utils import secure_filename

    UPLOAD_FOLDER = get_equipment_upload_folder()
    THUMB_FOLDER = get_equipment_thumb_folder()

    file = request.files.get("photo")
    remove_photo = request.form.get('remove_photo')
    filename = None
    
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get existing filename first
    cursor.execute("SELECT photo FROM equipment WHERE idk = %s", (id,))
    row = cursor.fetchone()
    old_photo = row['photo'] if row else None

    new_filename = old_photo  # default: keep existing

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(THUMB_FOLDER, exist_ok=True)


    if file:
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            return jsonify({"errors": {"photo": "Invalid file type"}}), 400

    try:
        if file:
            filename = process_image(file)
            filename = secure_filename(filename)

            # ext = file.filename.rsplit(".", 1)[-1].lower()
            # filename = f"{uuid.uuid4()}.{ext}"

            
            print(f"Saving file to {UPLOAD_FOLDER}/{filename}")

            # filepath = os.path.join(UPLOAD_FOLDER, filename)
            # file.save(filepath)
            
            new_filename = filename

            # delete old file if exists
            if old_photo:
                old_path = os.path.join(UPLOAD_FOLDER, old_photo)
                if os.path.exists(old_path):
                    os.remove(old_path)
                    
        elif remove_photo == '1' and old_photo:
            new_filename = None
            if old_photo:
                old_path = os.path.join(UPLOAD_FOLDER, old_photo)
                if os.path.exists(old_path):
                    os.remove(old_path)

        form_data = request.form

        cleaned, errors = validate_form(form_data, equipment_schema())

        if errors:
            return jsonify({"errors": errors}), 400

        idk = float(cleaned.get("idk")) if cleaned.get("idk") else None
        name = cleaned.get("name")
        brand = cleaned.get("brand")
        model = cleaned.get("model")
        year = int(cleaned.get("year")) if cleaned.get("year") else None
        life_span = (
            float(cleaned.get("life_span")) if cleaned.get("life_span") else None
        )
        maintenance_notes = cleaned.get("maintenance_notes")
        # photo = new_filename

        print("FORM:", request.form)
        print("FILES:", request.files)

        if filename:
            cursor.execute(
                """
                UPDATE equipment
                SET name=%s, brand=%s, model=%s, year=%s,
                    life_span=%s, maintenance_notes=%s, photo=%s
                WHERE idk=%s
            """,
                (name, brand, model, year, life_span, maintenance_notes, new_filename, id),
            )
        else:
            cursor.execute(
                """
                UPDATE equipment
                SET name=%s, brand=%s, model=%s, year=%s,
                    life_span=%s, maintenance_notes=%s
                WHERE idk=%s
            """,
                (name, brand, model, year, life_span, maintenance_notes, id),
            )

        conn.commit()

        return {"status": "ok"}

    except Exception as e:
        traceback.print_exc()   # 🔥 THIS is key
        return {"error": str(e)}, 500
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
        
# DELETE an equipment record by id

@main_bp.route('/equipment/<int:id>', methods=['DELETE'])
def delete_equipment(id):
    try:
        conn = exdb.connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM equipment WHERE idk = %s", (id,))
        conn.commit()

        return {"status": "deleted"}, 200

    except Exception as e:
        print(e)
        return {"error": "Failed to delete"}, 500

    finally:
        cursor.close()
        conn.close()

# GET maintenance records for an equipment by id

@main_bp.route('/equipment/<int:id>/maintenance')
def get_maintenance(id):
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT id, date, distance, type, shop, notes
        FROM equipment_maintenance
        WHERE equipment_id = %s
        ORDER BY date DESC
    """, (id,))

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)

# CREATE new maintenance record for an equipment by id

@main_bp.route('/equipment/<int:id>/maintenance', methods=['POST'])
def add_maintenance(id):
    data = request.get_json()

    date = data.get('date')
    distance = data.get('distance')
    type = data.get('type')
    shop = data.get('shop')
    notes = data.get('notes')

    conn = exdb.connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO equipment_maintenance 
        (equipment_id, date, distance, type, shop, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (id, date, distance, type, shop, notes))

    conn.commit()

    cursor.close()
    conn.close()

    return {"status": "ok"}, 201

# GET equipment photo


@main_bp.route("/images/equipment/<path:filename>")
def serve_equipment_image(filename):
    upload_folder = get_equipment_upload_folder()

    safe_path = os.path.normpath(filename)
    if safe_path.startswith(".."):
        abort(400)

    full_path = os.path.join(upload_folder, safe_path)

    if not os.path.exists(full_path):
        abort(404)

    response = send_from_directory(upload_folder, safe_path)
    response.cache_control.max_age = 604800
    response.cache_control.public = True
    return response

@main_bp.route('/images/equipment/thumbs/<filename>')
def get_thumb(filename):
    return send_from_directory(get_equipment_thumb_folder(), filename)

# UPDATE a maintenance record by id

@main_bp.route('/equipment/<int:id>/maintenance', methods=['PUT'])
def update_maintenance(id):
    data = request.get_json()
    
    conn = exdb.connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE equipment_maintenance
        SET date=%s, distance=%s, type=%s, shop=%s, notes=%s
        WHERE id=%s
    """, (data['date'], data['distance'], data['type'], data['shop'], data['notes'], id))

    conn.commit()
    return {"status": "ok"}

# DELETE a maintenance record by id

@main_bp.route('/equipment/<int:id>/maintenance', methods=['DELETE'])
def delete_maintenance(id):
    conn = exdb.connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipment_maintenance WHERE id=%s", (id,))
    conn.commit()
    return {"status": "deleted"}

# GET an individual health record byid


@main_bp.route("/health")
def health():
    try:
        startdate = request.args.get("start")
        enddate = request.args.get("end")
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health WHERE date BETWEEN %s and %s ORDER BY date"
        data = (startdate, enddate)
        cursor.execute(sql, data)
        health = cursor.fetchall()
        res = jsonify(health)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()


@main_bp.route("/health/<int:healthid>")
def readhealth(healthid):
    try:
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM health WHERE id=%s"
        cursor.execute(sql, healthid)
        health = cursor.fetchone()
        print(health)
        res = jsonify(health)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()


@main_bp.route("/health/last_known", methods=["GET"])
def get_last_known_weight():
    # Get the start date of your current window from the query params
    before_date = request.args.get("before")

    # Query for the single most recent record before that date
    query = """
        SELECT weight /1000 as weight, date 
        FROM health 
        WHERE date < %s AND weight IS NOT NULL 
        ORDER BY date DESC 
        LIMIT 1
    """
    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(query, (before_date))
    result = cursor.fetchone()
    return jsonify(result)

    # if result:
    #    return jsonify({'weight': result[0], 'date': result[1]})
    # return jsonify({'weight': 82.7, 'date': None}) # Fallback baseline


@main_bp.route("/stats")
def stats():
    try:
        startdate = request.args.get("start")
        enddate = request.args.get("end")
        conn = exdb.connect()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM stats WHERE date BETWEEN %s and %s ORDER BY date"
        data = (startdate, enddate)
        cursor.execute(sql, data)
        health = cursor.fetchall()
        res = jsonify(health)
        res.status_code = 200

        return res
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()


@main_bp.errorhandler(404)
def not_found(error=None):
    message = {
        "status": 404,
        "message": "There is no record: " + request.url,
    }
    res = jsonify(message)
    res.status_code = 404

    return res


# if __name__ == "__main__":

#     app.secret_key = 'super secret key'
#     app.config['SESSION_TYPE'] = 'filesystem'

#     #sess.init_app(app)

#     app.debug = True

#     app.run(host='0.0.0.0', port=5010)


def allowed_file(filename, allowed_extensions):
    print("Checking if file is allowed")
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions
