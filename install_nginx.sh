#!/usr/bin/env bash
# Install the ValenciaGuard nginx route into an existing server block.
#
# Usage:   sudo ./install_nginx.sh
# Env:     NGINX_SITE=/etc/nginx/sites-available/homeserver  (override to target another file)
#
# Idempotent: does nothing if the /valenciaguard/ location is already present.
set -euo pipefail

SITE="${NGINX_SITE:-/etc/nginx/sites-available/homeserver}"
CONF="$(dirname "$0")/deploy/nginx.conf"

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root: sudo $0" >&2
    exit 1
fi

if [[ ! -f "$SITE" ]]; then
    echo "Site config not found: $SITE (set NGINX_SITE to the right file)" >&2
    exit 1
fi

if grep -q 'location /valenciaguard/' "$SITE"; then
    echo "ValenciaGuard location already present in $SITE — nothing to do."
else
    BACKUP="$SITE.bak.$(date +%Y%m%d%H%M%S)"
    cp -a "$SITE" "$BACKUP"
    echo "Backup written: $BACKUP"

    # Strip comment lines, then insert the location blocks before the final
    # closing brace of the server block (the only unindented '}' line).
    grep -v '^\s*#' "$CONF" | sed -e 's/^/    /' > /tmp/vg-location.conf
    sed -i -e '/^}$/e cat /tmp/vg-location.conf' "$SITE"
    rm -f /tmp/vg-location.conf
    echo "Inserted /valenciaguard/ location into $SITE"
fi

nginx -t
systemctl reload nginx
echo "Done. ValenciaGuard is now routed at http://<host>/valenciaguard/"
echo "Make sure the app is running on 127.0.0.1:8473 with ROOT_PATH=/valenciaguard"
