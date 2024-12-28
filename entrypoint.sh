#!/bin/bash

# Set default values if environment variables are not set
DB_HOST=${MYSQL_HOST:-db}
DB_PORT=${MYSQL_PORT:-3306}

# Wait for the database to be ready
/app/wait-for-it.sh "$DB_HOST" "$DB_PORT" -- echo "Database is ready!"

# Apply database migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Execute the command passed to the container
exec "$@"
