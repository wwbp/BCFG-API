# Use Python 3.11-slim as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for building mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*


# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy only the Pipfile and Pipfile.lock to leverage Docker cache
COPY Pipfile Pipfile.lock /app/

# Install the project dependencies
RUN pipenv install --system --deploy --ignore-pipfile

# Copy the rest of the app files
COPY . /app/

# Expose port 80 for the application
EXPOSE 80
# Copy the wait-for-it script
COPY wait-for-it.sh /app/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run the application
CMD ["gunicorn", "bcfg_chat_api.wsgi:application", "--bind", "0.0.0.0:80", "--worker-class", "gevent", "--workers", "4"]
