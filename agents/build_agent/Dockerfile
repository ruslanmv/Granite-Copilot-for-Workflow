# Build agent Dockerfile
FROM python:3.11-slim

# Install Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy agent code and dependencies
COPY agent.py requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the agent
CMD ["python", "agent.py"]