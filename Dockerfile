# Use official Python runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for PostgreSQL client and builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first (leverage Docker cache)
COPY new/server/requirements.txt ./

# Install Python packages including production WSGI server (gunicorn) and postgres connector
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

# Copy the entire backend application into the container
COPY new/server/ ./

# Render automatically sets the PORT environment variable (default: 10000)
ENV PORT=10000
EXPOSE 10000

# Initialize DB tables and start Gunicorn WSGI server
CMD ["sh", "-c", "python -c 'from app import app, db; app.app_context().push(); db.create_all()' && exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120 'app:app'"]
