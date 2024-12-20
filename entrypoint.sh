#!/bin/bash

# Wait for the database to be ready
/app/wait-for-it.sh db 3306 -- echo "Database is ready!"

# Apply database migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Execute the command passed to the container
exec "$@"
