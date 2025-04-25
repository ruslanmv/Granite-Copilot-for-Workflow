# Compliance agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy agent code and dependencies
COPY agent.py requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the agent
CMD ["python", "agent.py"]