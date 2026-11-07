#!/bin/sh
set -e
if [ -n "$MYSQL_SSL_CA_B64" ]; then
  mkdir -p /tmp/certs
  python -c 'import os,base64,pathlib; path=pathlib.Path("/tmp/certs/aiven-ca.pem"); path.write_bytes(base64.b64decode(os.environ["MYSQL_SSL_CA_B64"]))'
  export MYSQL_SSL_CA=/tmp/certs/aiven-ca.pem
elif [ -n "$MYSQL_SSL_CA_PEM" ]; then
  mkdir -p /tmp/certs
  printf '%s\n' "$MYSQL_SSL_CA_PEM" > /tmp/certs/aiven-ca.pem
  export MYSQL_SSL_CA=/tmp/certs/aiven-ca.pem
fi
python -m alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
