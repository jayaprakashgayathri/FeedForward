#!/bin/sh
set -e

echo "⏳  Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."

until python -c "
import socket, sys, os
s = socket.socket()
s.settimeout(1)
try:
    s.connect((os.environ.get('POSTGRES_HOST','db'), int(os.environ.get('POSTGRES_PORT',5432))))
    s.close(); sys.exit(0)
except: sys.exit(1)
" 2>/dev/null; do
  sleep 1
done

echo "✅  PostgreSQL ready."
echo "🔧  Creating/verifying tables..."

python - <<'PY'
from app import create_app
from models import db
app = create_app()
with app.app_context():
    db.create_all()
    print("   Tables OK.")
PY

echo "🚀  Starting gunicorn..."
exec gunicorn \
  --bind "0.0.0.0:${PORT:-5000}" \
  --workers 2 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  "app:create_app()"
