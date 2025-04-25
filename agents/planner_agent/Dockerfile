# Planner agent Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy code and dependencies
COPY agent.py requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the planner agent
CMD ["python", "agent.py"]