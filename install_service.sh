#!/usr/bin/env bash
# Install ValenciaGuard as a systemd service running IN PLACE from this
# project directory (no copying to /opt, no dedicated system user).
# Run with sudo from the repository root:  sudo ./install_service.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="${SUDO_USER:-$(stat -c '%U' "$PROJECT_DIR")}"
UNIT=/etc/systemd/system/valenciaguard.service

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root: sudo $0" >&2
    exit 1
fi

if [[ ! -x "$PROJECT_DIR/.venv/bin/uvicorn" ]]; then
    echo "No virtualenv found at $PROJECT_DIR/.venv" >&2
    echo "Create it first:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "No .env found — copying .env.example. Edit it before starting the service."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    chown "$APP_USER:$APP_USER" "$PROJECT_DIR/.env"
fi

echo "==> Installing systemd unit (runs as ${APP_USER} from ${PROJECT_DIR})"
cp "$PROJECT_DIR/deploy/valenciaguard.service" "$UNIT"
systemctl daemon-reload
systemctl enable valenciaguard

echo "==> nginx"
echo "    The app mounts under /valenciaguard/ on the EXISTING nginx server."
echo "    To add the route, run:  sudo ./install_nginx.sh"

cat <<EOF

Done. Next steps:
  1. Check .env in this directory:
       - SECRET_KEY set to a long random string
       - ROOT_PATH=/valenciaguard
       - DATABASE_URL (postgres or sqlite)
       - optionally KIMI_API_KEY, SMTP_*, CJK_FONT_PATH
  2. Seed the database (first time only):
       .venv/bin/python scripts/seed.py
  3. Start the service:  sudo systemctl start valenciaguard
     (listens on 127.0.0.1:8473; code edits apply after
      'sudo systemctl restart valenciaguard')
  4. Add the nginx route:  sudo ./install_nginx.sh
  5. Optional cron for alerts:
       0 8 * * * ${APP_USER} cd ${PROJECT_DIR} && .venv/bin/python -m app.services.alerts
EOF
