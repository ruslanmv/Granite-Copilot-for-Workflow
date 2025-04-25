FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .

# Ensure .env is loaded
ENV PYTHONUNBUFFERED=1

CMD ["python", "agent.py"]
