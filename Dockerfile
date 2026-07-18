# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed (none strictly required for these python libraries, but curl/git are good practice)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose ports if MCP stdio-based servers ever run as SSE hosts (optional but good practice)
EXPOSE 8000

# Default command: Run the FastAPI web server
# Use shell form to expand the $PORT variable provided by Render
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
