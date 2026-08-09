#!/usr/bin/env python3
"""
migrate_tokenstore.py

Copy or move an existing global Garmin tokenstore file/directory into a
per-user tokenstore file used by the app (appends ".<user_id>").

Usage examples:
  python migrate_tokenstore.py --user-id 42
  python migrate_tokenstore.py --user-id 42 --tokenstore ~/.garminconnect --move

This script is intentionally conservative: it will not try to guess which
user should receive tokens. Provide `--user-id` for the account that should
receive the existing tokenstore.
"""

from __future__ import annotations
import argparse
import os
import shutil
import sys
from pathlib import Path

# Load app config to get default tokenstore locations
try:
    import config as app_config
except Exception:
    app_config = None


def migrate(tokenstore_path: str | None, tokenstore_base64_path: str | None, user_id: int, move: bool = False) -> int:
    """Copy/move tokenstore files to per-user files suffixed with .<user_id>.

    Returns 0 on success, non-zero on failure.
    """
    if not tokenstore_path and not tokenstore_base64_path:
        print("No tokenstore path provided and config not available.")
        return 2

    errors = False

    for path in (tokenstore_path, tokenstore_base64_path):
        if not path:
            continue

        src = os.path.expanduser(path)
        if not os.path.exists(src):
            print(f"Skipping missing tokenstore: {src}")
            continue

        dst = src + f'.{user_id}'

        try:
            # If source is a directory, copytree; otherwise copy file
            if os.path.isdir(src):
                # If dst exists, avoid overwriting unless explicit
                if os.path.exists(dst):
                    print(f"Destination already exists, skipping: {dst}")
                else:
                    shutil.copytree(src, dst)
                    print(f"Copied directory {src} -> {dst}")
            else:
                # Ensure destination directory exists
                os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
                if os.path.exists(dst):
                    print(f"Destination file already exists, skipping: {dst}")
                else:
                    shutil.copy2(src, dst)
                    print(f"Copied file {src} -> {dst}")

            if move:
                # Remove original (file or directory)
                if os.path.isdir(src):
                    shutil.rmtree(src)
                else:
                    os.remove(src)
                print(f"Removed original tokenstore: {src}")

        except Exception as e:
            print(f"ERROR migrating {src} -> {dst}: {e}")
            errors = True

    return 1 if errors else 0


def main(argv=None):
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(description="Migrate global Garmin tokenstore to per-user token file(s)")
    p.add_argument("--user-id", type=int, required=True, help="Numeric user id to target")
    p.add_argument("--tokenstore", help="Path to global tokenstore file/dir (overrides config)")
    p.add_argument("--tokenstore-base64", help="Path to alternative base64 tokenstore (overrides config)")
    p.add_argument("--move", action="store_true", help="Move files instead of copying")
    args = p.parse_args(argv)

    tokenstore = args.tokenstore
    tokenstore_base64 = args.tokenstore_base64

    if not tokenstore and app_config is not None:
        tokenstore = getattr(app_config.Config(), 'tokenstore', None)
    if not tokenstore_base64 and app_config is not None:
        tokenstore_base64 = getattr(app_config.Config(), 'tokenstore_base64', None)

    if not tokenstore and not tokenstore_base64:
        print("No tokenstore paths are available (neither passed nor found in config). Exiting.")
        return 2

    return migrate(tokenstore, tokenstore_base64, args.user_id, move=args.move)


if __name__ == '__main__':
    raise SystemExit(main())
