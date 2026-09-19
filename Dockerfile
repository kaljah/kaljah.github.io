# Use official Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY new/server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

# Copy backend application code
COPY new/server/ ./

ENV PORT=10000
EXPOSE 10000

# Start Gunicorn WSGI server
CMD ["sh", "-c", "python -c 'from app import app, db; app.app_context().push(); db.create_all()' && exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120 'app:app'"]
