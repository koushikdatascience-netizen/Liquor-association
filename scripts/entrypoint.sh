#!/bin/sh
set -e

python -c "import os; from urllib.parse import urlparse; url=os.environ.get('DATABASE_URL', ''); parsed=urlparse(url); print('DATABASE_URL host:', parsed.hostname or 'not configured')"

attempt=1
until python manage.py migrate --noinput; do
  if [ "$attempt" -ge 10 ]; then
    echo "Database migration failed after $attempt attempts."
    exit 1
  fi
  echo "Database is not ready yet. Retrying in 5 seconds... ($attempt/10)"
  attempt=$((attempt + 1))
  sleep 5
done

python manage.py ensure_admin
python manage.py collectstatic --noinput

exec "$@"
