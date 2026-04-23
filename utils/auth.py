"""
utils/auth.py
Simple environment-backed authentication helpers.

Usage:
 - Set `APP_USERS` in .env as comma-separated `user:pass` pairs.
 - Optionally set `ADMIN_USER`/`ADMIN_PASS` as a single admin entry.

This is intentionally minimal and intended for local/demo use only.
"""

import os
import json
from pathlib import Path
from typing import Dict


def _users_json_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "data" / "users.json"


def load_users() -> Dict[str, str]:
    """Return a dict of username -> password.

    Priority:
    1. `data/users.json` (project-relative) if present — expected format: {"user":"pass", ...}
    2. Fallback to `APP_USERS` and `ADMIN_USER`/`ADMIN_PASS` from environment.
    """
    users: Dict[str, str] = {}

    # 1) JSON file (preferred)
    jpath = _users_json_path()
    if jpath.exists():
        try:
            raw = json.loads(jpath.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    users[str(k)] = str(v)
                return users
        except Exception:
            # ignore parse errors and fall back to env
            pass

    # 2) Env fallback
    raw = os.getenv("APP_USERS", "").strip()
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for part in parts:
            if ":" in part:
                u, pw = part.split(":", 1)
                users[u.strip()] = pw.strip()

    admin_user = os.getenv("ADMIN_USER")
    admin_pass = os.getenv("ADMIN_PASS")
    if admin_user and admin_pass:
        users[admin_user] = admin_pass

    return users


def authenticate(username: str, password: str) -> bool:
    """Return True if username/password match a stored entry."""
    if not username or not password:
        return False
    users = load_users()
    return users.get(username) == password


def save_users(users: Dict[str, str]):
    """Write the users dict to `data/users.json` (overwrites).

    Note: simple helper for CLI/script usage; not used by the UI right now.
    """
    jpath = _users_json_path()
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(users, indent=2), encoding="utf-8")
