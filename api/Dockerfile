FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Use shell form to expand the $PORT variable provided by Render
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
