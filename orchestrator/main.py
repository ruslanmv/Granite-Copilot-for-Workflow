# orchestrator/main.py

import os
import logging
import yaml
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from nats.aio.client import Client as NATS

from orchestrator.bus import NATSPubSub
from orchestrator.llm_client import LLMClient
from orchestrator.graph_tracer import GraphTracer
from orchestrator.config import load_config

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

# Load YAML config (interpolates ENV vars)
CONFIG_PATH = Path(__file__).parent / "config.yaml"
CONFIG = load_config(CONFIG_PATH)

# FastAPI app
app = FastAPI(title="Granite Copilot Orchestrator")

# NATS client and orchestrator bus (initialized on startup)
nats = NATS()
bus: NATSPubSub

# Set up GraphTracer with Neo4j credentials
tracer = GraphTracer(
    uri=os.getenv("NEO4J_URI", CONFIG["neo4j_uri"]),
    user=os.getenv("NEO4J_USER", CONFIG["neo4j_user"]),
    pwd=os.getenv("NEO4J_PASSWORD", CONFIG["neo4j_password"])
)

# Initialize LLM client
llm = LLMClient(
    model_id=CONFIG["llm"]["model_id"],
    decoding_method="greedy",
    max_new_tokens=CONFIG["llm"]["timeout_secs"]
)


class WorkflowYAML(BaseModel):
    __root__: str  # raw YAML string


class RunRequest(BaseModel):
    overrides: dict = {}


@app.on_event("startup")
async def startup_event():
    global bus
    # Connect to NATS
    await nats.connect(servers=[CONFIG["nats_url"]])
    bus = NATSPubSub(nats, tracer)

    # Subscribe to planner and autofix responses
    await bus.subscribe("workflow.plan.response", handle_plan_response)
    await bus.subscribe("workflow.autofix.response", handle_autofix_response)

    logger.info("Orchestrator connected to NATS and subscriptions set up")


@app.on_event("shutdown")
async def shutdown_event():
    # Gracefully close NATS connection
    await nats.drain()


@app.post("/api/workflows", status_code=201)
async def create_workflow(workflow: WorkflowYAML):
    try:
        spec = yaml.safe_load(workflow.__root__)
        workflow_id = spec.get("name")
        if not workflow_id:
            raise ValueError("Missing 'name' field in workflow spec")
        tracer.create_workflow_node(workflow_id, spec)
        # Persist spec to object store or filesystem as needed
        return {"workflowId": workflow_id, "message": "Workflow created"}
    except Exception as e:
        logger.error("Failed to create workflow: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/workflows")
async def list_workflows():
    return tracer.list_workflows()


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    spec = tracer.get_workflow_spec(workflow_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return spec


@app.post("/api/workflows/{workflow_id}/runs", status_code=202)
async def run_workflow(workflow_id: str, req: RunRequest):
    spec = tracer.get_workflow_spec(workflow_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Workflow not found")
    run_id = await bus.start_run(workflow_id, spec, req.overrides)
    return {"runId": run_id, "status": "scheduled"}


@app.get("/api/runs/{run_id}")
async def get_run_status(run_id: str):
    status = tracer.get_run_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    # Subscribe to all workflow events
    sub = await nats.subscribe("workflow.events.>", queue="ws_group")
    try:
        async for msg in sub.messages:
            await ws.send_text(msg.data.decode())
    except WebSocketDisconnect:
        await sub.unsubscribe()


# Internal message handlers

async def handle_plan_response(msg):
    data = yaml.safe_load(msg.data.decode())
    dag = data.get("dag")
    run_id = data.get("runId")
    await bus.dispatch_tasks(run_id, dag)


async def handle_autofix_response(msg):
    data = yaml.safe_load(msg.data.decode())
    run_id = data.get("runId")
    patch = data.get("patch")
    await bus.apply_patch_and_retry(run_id, patch)
