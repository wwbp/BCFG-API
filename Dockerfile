# Use Python 3.11-slim as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy only the Pipfile and Pipfile.lock to leverage Docker cache
COPY Pipfile Pipfile.lock /app/

# Install the project dependencies
RUN pipenv install --system --deploy --ignore-pipfile

# Copy the rest of the app files
COPY . /app/

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput

# Expose port 80 for the application
EXPOSE 80

# Command to run the application using Gunicorn
CMD ["gunicorn", "bcfg_chat_api.wsgi:application", "--bind", "0.0.0.0:80"]
