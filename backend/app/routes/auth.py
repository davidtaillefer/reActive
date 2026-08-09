import pymysql.cursors
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import exdb

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    payload = request.get_json() or {}
    username = payload.get('username')
    password = payload.get('password')

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'invalid credentials'}), 401

        pw_hash = user.get('password_hash')
        if not pw_hash or not check_password_hash(pw_hash, password):
            return jsonify({'error': 'invalid credentials'}), 401

        # Success — store user id in session
        session['user_id'] = int(user['id'])
        return jsonify({'status': 'ok', 'user_id': user['id']})
    except Exception as e:
        current_app.logger.exception('Login error')
        return jsonify({'error': 'server error'}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    payload = request.get_json() or {}
    username = payload.get('username')
    password = payload.get('password')
    email = payload.get('email')

    # Debug: log what keys were received (do not log password value)
    try:
        current_app.logger.debug('Register called; keys=%s username=%s email=%s', list(payload.keys()), username, email)
    except Exception:
        pass

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    pw_hash = generate_password_hash(password)

    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # Check for existing username or email
        cursor.execute("SELECT id FROM users WHERE username=%s OR (email IS NOT NULL AND email=%s)", (username, email))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'error': 'username or email already exists'}), 409

        cursor.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (%s, %s, %s, NOW())",
            (username, email, pw_hash)
        )
        conn.commit()
        new_id = cursor.lastrowid

        # Auto-login the new user
        session['user_id'] = int(new_id)
        return jsonify({'status': 'ok', 'user_id': new_id}), 201
    except Exception as e:
        current_app.logger.exception('Register error')
        return jsonify({'error': 'server error'}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'status': 'ok'})


@auth_bp.route('/auth/me', methods=['GET'])
def me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'user': None}), 200

    conn = exdb.connect()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT id, username, email, is_active, role, created_at FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'user': None}), 200
        return jsonify({'user': user}), 200
    except Exception:
        return jsonify({'user': None}), 200
    finally:
        cursor.close()
        conn.close()
