#!/usr/bin/env python3
"""Debug script to check if routes are registered correctly."""

import sys
import traceback

print("=" * 60)
print("CHECKING ROUTE REGISTRATION")
print("=" * 60)

try:
    print("\n[1/5] Importing Flask...")
    from flask import Flask
    print("✓ Flask imported successfully")
except Exception as e:
    print(f"✗ Failed to import Flask: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[2/5] Creating Flask app...")
    from app import create_app
    app = create_app()
    print("✓ Flask app created successfully")
except Exception as e:
    print(f"✗ Failed to create app: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[3/5] Checking registered routes...")
    print("\nAll routes in the app:")
    sync_routes = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if 'sync' in rule.rule or 'cred' in rule.rule:
            methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print(f"  {rule.rule:50} [{methods}]")
            sync_routes.append(rule.rule)
    
    print(f"\n✓ Found {len(sync_routes)} sync/credentials routes")
    
except Exception as e:
    print(f"✗ Failed to check routes: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[4/5] Checking sync blueprint...")
    from app.routes.sync import sync_bp
    print(f"Blueprint name: {sync_bp.name}")
    print(f"Blueprint import_name: {sync_bp.import_name}")
    print("✓ sync_bp imported successfully")
except Exception as e:
    print(f"✗ Failed to import sync_bp: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[5/5] Checking config...")
    from app.routes.sync import config
    print(f"config.email: {config.email}")
    print(f"config.password: {'*' * len(config.password) if config.password else None}")
    print(f"config.tokenstore: {config.tokenstore}")
    print("✓ config imported successfully")
except Exception as e:
    print(f"✗ Failed to import config: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

expected_routes = [
    '/sync',
    '/sync/days/<int:days>',
    '/sync/credentials/status',
    '/sync/credentials',
    '/sync/credentials/mfa',
    '/sync/credentials/logout'
]

missing = [r for r in expected_routes if r not in sync_routes]
if missing:
    print(f"\n✗ MISSING ROUTES ({len(missing)}):")
    for route in missing:
        print(f"  - {route}")
else:
    print("\n✓ ALL EXPECTED ROUTES ARE REGISTERED")

if sync_routes:
    print(f"\n✓ Total sync routes: {len(sync_routes)}")
else:
    print("\n✗ NO SYNC ROUTES FOUND!")
