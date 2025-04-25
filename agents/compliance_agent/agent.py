import os
import sys
import asyncio
import json
import logging
from nats.aio.client import Client as NATS
from opa import OpaClient

# Configure logging
global_logger = logging.getLogger("compliance_agent")
global_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
global_logger.addHandler(handler)

# Environment variables
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
OPA_URL = os.getenv("OPA_URL", "http://opa:8181/v1/data")
SUBJECT = "verify.opa.request"

# Initialize OPA client
opa_client = OpaClient(base_url=OPA_URL)

async def run_compliance_check(task_payload: dict) -> dict:
    """
    Sends payload to OPA for policy evaluation.
    Expects payload fields:
      - input: dict (task output to validate)
    Returns pass/fail and any policy violations.
    """
    input_data = task_payload.get("output", {})
    global_logger.info("Running compliance check with OPA...")

    result = opa_client.evaluate(input_data)
    violations = result.get("result", [])
    status = "pass" if not violations else "fail"

    return {"status": status, "violations": violations}

async def message_handler(msg):
    try:
        data = json.loads(msg.data.decode())
        run_id = data.get("runId")
        task_id = data.get("taskId")
        payload = data.get("payload", {})
        global_logger.info(f"Received compliance request for task {task_id}")

        result = await run_compliance_check(payload)
        response = {
            "runId": run_id,
            "taskId": task_id,
            "status": result["status"],
            "output": {"violations": result.get("violations", [])}
        }

        await msg.respond(json.dumps(response).encode())
        global_logger.info(f"Published compliance response for task {task_id} (status={result['status']})")
    except Exception as e:
        global_logger.error(f"Error handling compliance request: {e}")

async def main():
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    global_logger.info(f"Connected to NATS at {NATS_URL}")

    sub = await nc.subscribe(SUBJECT)
    global_logger.info(f"Subscribed to subject {SUBJECT}")

    async for msg in sub.messages:
        asyncio.create_task(message_handler(msg))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        global_logger.info("Compliance agent shutting down...")