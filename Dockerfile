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
EXPOSE 8080

# Default command: prints usage. Teammates can override this to run ingestion or the orchestrator.
CMD ["python", "-c", "print('VeriTrace Help Bot Container is Ready!\\n\\nTo ingest documentation:\\n  docker run --env-file .env <image_name> python rag/ingest.py\\n\\nTo run the interactive CLI Bot:\\n  docker run -it --env-file .env <image_name> python orchestrator/main.py')"]
