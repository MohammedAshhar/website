import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_ADMIN_USER = os.environ.get("ADMIN_USER") or "admin"
DEFAULT_ADMIN_PASS = os.environ.get("ADMIN_PASS") or "admin123"
OWNER_USER = os.environ.get("OWNER_USER") or "owner"
OWNER_PASS = os.environ.get("OWNER_PASS") or "owner123"
DESK_USER = os.environ.get("DESK_USER") or "deskmanager"
DESK_PASS = os.environ.get("DESK_PASS") or "desk123"

if not os.environ.get("ADMIN_USER"):
    print("WARNING: ADMIN_USER not set in .env or environment. Using default 'admin'.")
if not os.environ.get("ADMIN_PASS"):
    print("WARNING: ADMIN_PASS not set in .env or environment. Using default 'admin123'.")
if not os.environ.get("OWNER_USER"):
    print("WARNING: OWNER_USER not set in .env or environment. Using default 'owner'.")
if not os.environ.get("OWNER_PASS"):
    print("WARNING: OWNER_PASS not set in .env or environment. Using default 'owner123'.")
if not os.environ.get("DESK_USER"):
    print("WARNING: DESK_USER not set in .env or environment. Using default 'deskmanager'.")
if not os.environ.get("DESK_PASS"):
    print("WARNING: DESK_PASS not set in .env or environment. Using default 'desk123'.")

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "generated_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


if __name__ == "__main__":
    from .database import Database
    from .api import create_fastapi_app

    database = Database()
    database.seed_doctors()
    database.seed_tests()
    database.create_admin_user(DEFAULT_ADMIN_USER, _hash_password(DEFAULT_ADMIN_PASS))
    database.create_admin_user(OWNER_USER, _hash_password(OWNER_PASS), role="owner")
    database.create_admin_user(DESK_USER, _hash_password(DESK_PASS), role="desk")
    database.seed_default_permissions()
    api = create_fastapi_app(database)
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    print(f"Unicus Diagnostics + Admin running at http://localhost:{port}")
    uvicorn.run(api, host="0.0.0.0", port=port)
