"""Create a new employee (admin-role) account directly in the database.

Usage:
    sudo .venv/bin/python scripts/add_admin.py <username> [password]

If the password is omitted it is prompted for (no echo).
Reads DATABASE_URL from .env like the app itself (PostgreSQL or SQLite).

Note: this creates an EMPLOYEE (admin) account. Only do this as the
superuser (agency boss) — the same rule the Users page enforces.
"""
import getpass
import os
import sys
from pathlib import Path

# allow running with a bare/system python (e.g. `sudo python ...`): if the
# app dependencies are missing, re-exec with the project venv interpreter
_VENV_PY = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
try:
    import sqlmodel  # noqa: F401
except ModuleNotFoundError:
    if _VENV_PY.exists() and Path(sys.executable) != _VENV_PY:
        os.execv(str(_VENV_PY), [str(_VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])
    raise

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.auth import hash_password
from app.database import engine, init_db
from app.models import User

MIN_PASSWORD_LEN = 8


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    username = sys.argv[1].strip()
    if not username:
        print("Error: username cannot be empty.")
        sys.exit(1)

    if len(sys.argv) >= 3:
        password = sys.argv[2]
    else:
        password = getpass.getpass("Password: ")
        if getpass.getpass("Repeat password: ") != password:
            print("Error: passwords do not match.")
            sys.exit(1)
    if len(password) < MIN_PASSWORD_LEN:
        print(f"Error: password must be at least {MIN_PASSWORD_LEN} characters "
              f"(received {len(password)}).")
        sys.exit(1)

    init_db()
    with Session(engine) as session:
        if session.exec(select(User).where(User.username == username)).first():
            print(f"Error: user '{username}' already exists.")
            sys.exit(1)
        user = User(username=username, password_hash=hash_password(password), role="admin")
        session.add(user)
        session.commit()
        session.refresh(user)
    print(f"Employee account created: {username} (role=admin, id={user.id})")
    print("Tell them to log in and change the password soon.")


if __name__ == "__main__":
    main()
