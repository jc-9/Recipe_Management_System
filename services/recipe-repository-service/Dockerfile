# Dockerfile for recipe-repository-service
# Use Python 3.12.9 as specified
FROM python:3.12.9-slim-bookworm

# Set working directory inside the container
WORKDIR /app

# Install system dependencies if any are needed for Python packages
# (e.g., libpq-dev for psycopg2-binary, build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the entire application code
COPY ./app /app/app

# Expose the port your FastAPI application will run on
EXPOSE 8000

# Command to run the application using uvicorn (an ASGI server)
# --host 0.0.0.0 makes it accessible from outside the container
# app.main:app refers to the 'app' object in 'main.py' within the 'app' directory
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]