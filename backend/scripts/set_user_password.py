#!/usr/bin/env python3
"""One-off script to set a user's password hash in the `users` table.

Usage: python set_user_password.py <username_or_id> <new_password>
"""
import sys
from werkzeug.security import generate_password_hash
import pymysql
from config import Config


def main():
    if len(sys.argv) < 3:
        print("Usage: set_user_password.py <username_or_id> <new_password>")
        sys.exit(2)

    who = sys.argv[1]
    pw = sys.argv[2]
    pw_hash = generate_password_hash(pw)

    conn = pymysql.connect(host=Config.MYSQL_DATABASE_HOST,
                           user=Config.MYSQL_DATABASE_USER,
                           password=Config.MYSQL_DATABASE_PASSWORD,
                           db=Config.MYSQL_DATABASE_DB,
                           port=Config.MYSQL_DATABASE_PORT,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            if who.isdigit():
                cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (pw_hash, int(who)))
            else:
                cur.execute("UPDATE users SET password_hash=%s WHERE username=%s", (pw_hash, who))
        conn.commit()
        print("Password updated.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
