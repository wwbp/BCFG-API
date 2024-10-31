FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy Pipfile and Pipfile.lock to the working directory
COPY Pipfile Pipfile.lock /app/

# Install pipenv and project dependencies
RUN pip install pipenv && pipenv install --system --deploy

# Copy the rest of the application code to the working directory
COPY . /app

# Expose the port that Flask will run on
EXPOSE 5000

# Set the environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Command to run the Flask app
CMD ["gunicorn", "-w", "4", "app:app", "--bind", "0.0.0.0:5000"]

