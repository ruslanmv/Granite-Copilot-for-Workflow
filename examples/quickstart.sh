#!/usr/bin/env bash
set -euo pipefail

# Quickstart script for Granite-Copilot-for-Workflow demo

# 1. Ensure .env is populated
if [ ! -f .env ]; then
  echo "Copying .env.template to .env (edit with your credentials)..."
  cp ../.env.template .env
  echo "Please edit .env and rerun this script."
  exit 1
fi

# 2. Start core services
echo "🚀 Starting NATS, Neo4j, OPA, Orchestrator, and all agents..."
docker compose up -d

# 3. Wait for services to become healthy
echo "🔄 Waiting for containers to be healthy..."
timeout=60
count=0
while [ $count -lt $timeout ]; do
  unhealthy=$(docker compose ps --services --filter "status=running" | wc -l)
  total=$(docker compose ps --services | wc -l)
  if [ "$unhealthy" -eq "$total" ]; then
    echo "✅ All services are running."
    break
  fi
  sleep 1
  count=$((count + 1))
done
if [ $count -ge $timeout ]; then
  echo "⚠️ Some services failed to start in time."
  docker compose ps
  exit 1
fi

# 4. Apply example DAG
echo "📑 Loading example workflow from examples/nightly_build.yaml..."
curl -sX POST \
  http://localhost:8080/api/workflows \
  -H "Content-Type: application/x-yaml" \
  --data-binary @../examples/nightly_build.yaml \
  && echo "✅ Example workflow created."

# 5. Open frontend UI
echo "🌐 Opening frontend UI at http://localhost:3000"
if command -v xdg-open >/dev/null; then
  xdg-open http://localhost:3000
elif command -v open >/dev/null; then
  open http://localhost:3000
else
  echo "Please open http://localhost:3000 in your browser."
fi

# 6. Tail logs for quick feedback
echo "📜 Tailing orchestrator logs (CTRL+C to exit)..."
docker compose logs -f orchestrator
