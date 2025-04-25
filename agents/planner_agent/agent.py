import os
import sys
import asyncio
import json
import logging
from nats.aio.client import Client as NATS
from orchestrator.llm_client import LLMClient

# Configure logging
global_logger = logging.getLogger("planner_agent")
global_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
global_logger.addHandler(handler)

# Environment variables
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
PLAN_REQUEST_SUBJECT = "workflow.plan.request"
PLAN_RESPONSE_SUBJECT = "workflow.plan.response"

async def message_handler(msg):
    """
    Handle planning requests: invoke LLM to convert natural-language or YAML into DAG JSON.
    Expected payload: { text: str, workflowId: str, runId: str, replyTo: subject }
    """
    try:
        data = json.loads(msg.data.decode())
        prompt = data.get("text") or ""
        workflow_id = data.get("workflowId")
        run_id = data.get("runId")
        reply_to = data.get("replyTo", PLAN_RESPONSE_SUBJECT)
        global_logger.info(f"Received plan request for workflow {workflow_id}, run {run_id}")

        llm = LLMClient()
        # Craft prompt for planning
        plan_prompt = f"Generate a JSON DAG for workflow '{workflow_id}' based on: {prompt}"  
        plan_json = llm.generate_text(plan_prompt)

        # Parse LLM output into JSON
        dag = json.loads(plan_json)

        response = {"workflowId": workflow_id, "runId": run_id, "dag": dag}
        await msg.respond(json.dumps(response).encode())
        global_logger.info(f"Published plan response for run {run_id}")
    except Exception as e:
        global_logger.error(f"Error in planner_agent: {e}")

async def main():
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    global_logger.info(f"Connected to NATS at {NATS_URL}")

    # Subscribe to plan requests
    sub = await nc.subscribe(PLAN_REQUEST_SUBJECT)
    global_logger.info(f"Subscribed to subject {PLAN_REQUEST_SUBJECT}")

    async for msg in sub.messages:
        asyncio.create_task(message_handler(msg))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        global_logger.info("Planner agent shutting down...")