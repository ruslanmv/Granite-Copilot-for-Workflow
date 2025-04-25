import os
import sys
import subprocess
import asyncio
import json
import logging
from nats.aio.client import Client as NATS

# Configure logging
global_logger = logging.getLogger("build_agent")
global_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
global_logger.addHandler(handler)

# Environment variables
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
SUBJECT = "task.docker-build.request"

async def run_build(task_payload: dict) -> dict:
    """
    Performs a Docker build based on the task payload.
    Expects payload fields:
      - context: str (build context directory)
      - image: str (target image tag)
    Returns a result dict with status and logs.
    """
    context = task_payload.get("context", ".")
    image = task_payload.get("image")
    cmd = ["docker", "build", "-t", image, context]
    global_logger.info(f"Running build: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    logs = []
    for line in proc.stdout:
        global_logger.info(line.strip())
        logs.append(line)

    return_code = proc.wait()
    status = "pass" if return_code == 0 else "fail"

    return {"status": status, "logs": "".join(logs)}

async def message_handler(msg):
    try:
        data = json.loads(msg.data.decode())
        run_id = data.get("runId")
        task_id = data.get("taskId")
        payload = data.get("payload", {})
        global_logger.info(f"Received build request for task {task_id}")

        result = await run_build(payload)
        response = {
            "runId": run_id,
            "taskId": task_id,
            "status": result["status"],
            "output": {"logs": result["logs"]}
        }

        await msg.respond(json.dumps(response).encode())
        global_logger.info(f"Published build response for task {task_id} (status={result['status']})")
    except Exception as e:
        global_logger.error(f"Error handling build request: {e}")

async def main():
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    global_logger.info(f"Connected to NATS at {NATS_URL}")

    # Subscribe to build requests
    sub = await nc.subscribe(SUBJECT)
    global_logger.info(f"Subscribed to subject {SUBJECT}")

    async for msg in sub.messages:
        asyncio.create_task(message_handler(msg))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        global_logger.info("Build agent shutting down...")