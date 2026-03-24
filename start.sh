#!/bin/sh
# script to wait for database to be ready before starting app
set -e

echo "Waiting for MySQL..."
while ! python -c "import socket; s = socket.create_connection(('$DATABASE_HOST', int('$DATABASE_PORT')), timeout=2); s.close()" 2>/dev/null; do
  sleep 1
done
echo "MySQL is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Seeding demo database..."
python manage.py seed_database

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"

