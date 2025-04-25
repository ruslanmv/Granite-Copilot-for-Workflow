# Security agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install scanning tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    # Install Trivy
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin && \
    # Install Snyk
    npm install -g snyk && \
    rm -rf /var/lib/apt/lists/*

# Copy agent code and dependencies
COPY agent.py requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the agent
CMD ["python", "agent.py"]