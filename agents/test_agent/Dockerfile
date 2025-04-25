# Test agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install pytest and JSON plugin
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py ./

# Run the test agent
CMD ["python", "agent.py"]
