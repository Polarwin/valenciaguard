#!/usr/bin/env bash
# Install ValenciaGuard as a systemd service behind nginx on Ubuntu.
# Run as root (or with sudo) from the repository root.
set -euo pipefail

APP_USER=valenciaguard
APP_DIR=/opt/valenciaguard
DATA_DIR=/var/lib/valenciaguard

echo "==> Creating user ${APP_USER}"
id -u ${APP_USER} >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin ${APP_USER}

echo "==> Creating directories"
mkdir -p ${APP_DIR} ${DATA_DIR}/uploads
cp -r app static scripts requirements.txt ${APP_DIR}/
[ -f .env ] && cp .env ${APP_DIR}/.env || cp .env.example ${APP_DIR}/.env
chown -R ${APP_USER}:${APP_USER} ${APP_DIR} ${DATA_DIR}
chmod 600 ${APP_DIR}/.env

echo "==> Creating virtualenv and installing dependencies"
python3 -m venv ${APP_DIR}/.venv
${APP_DIR}/.venv/bin/pip install --upgrade pip
${APP_DIR}/.venv/bin/pip install -r ${APP_DIR}/requirements.txt

echo "==> Installing systemd unit"
cp deploy/valenciaguard.service /etc/systemd/system/valenciaguard.service
systemctl daemon-reload
systemctl enable valenciaguard

echo "==> nginx"
echo "    The app mounts under /valenciaguard/ on the EXISTING nginx server."
echo "    Merge the location blocks from deploy/nginx.conf into your existing"
echo "    server {} (the script does NOT create a new vhost)."

cat <<EOF

Done. Next steps:
  1. Edit ${APP_DIR}/.env:
       - set SECRET_KEY to a long random string
       - set ROOT_PATH=/valenciaguard
       - set UPLOAD_DIR=${DATA_DIR}/uploads
       - set DATABASE_URL (sqlite:////var/lib/valenciaguard/valenciaguard.db is fine)
       - optionally KIMI_API_KEY, SMTP_*, CJK_FONT_PATH
  2. Seed the database:
       sudo -u ${APP_USER} ${APP_DIR}/.venv/bin/python -m scripts.seed
       (run from ${APP_DIR})
  3. Start the service:  systemctl start valenciaguard  (listens on 127.0.0.1:8473)
  4. Add the location blocks from deploy/nginx.conf to your existing nginx
     server {} and reload nginx (nginx -t && systemctl reload nginx).
  5. Optional cron for alerts:
       0 8 * * * ${APP_USER} cd ${APP_DIR} && .venv/bin/python -m app.services.alerts
EOF
