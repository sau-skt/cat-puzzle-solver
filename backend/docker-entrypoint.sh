#!/bin/sh
set -e
if [ -n "$MYSQL_SSL_CA_PEM" ]; then
  mkdir -p /tmp/certs
  printf '%s\n' "$MYSQL_SSL_CA_PEM" > /tmp/certs/aiven-ca.pem
  export MYSQL_SSL_CA=/tmp/certs/aiven-ca.pem
fi
python -m alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
