# orchestrator/Dockerfile
# -----------------------
# Builds the FastAPI‐based orchestrator service for Granite-Copilot-for-Workflow.

FROM python:3.11-slim AS runtime

# 1. Environment hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# 2. Install system-level deps (curl→ca-certs already in slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Python deps
#    (For production you can pin versions in a requirements.txt or poetry.lock
#     but inline keeps this image self-contained.)
RUN pip install --no-cache-dir \
        fastapi \
        "uvicorn[standard]" \
        pydantic \
        nats-py \
        PyYAML \
        python-dotenv \
        ibm-watsonx-ai \
        neo4j \
        aiohttp

# 4. Copy orchestrator source
COPY orchestrator /app

# 5. Expose HTTP port
EXPOSE 8080

# 6. Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
