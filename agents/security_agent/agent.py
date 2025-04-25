import os
import sys
import asyncio
import json
import logging
from nats.aio.client import Client as NATS
from subprocess import PIPE, STDOUT, Popen

# Configure logging
global_logger = logging.getLogger("security_agent")
global_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
global_logger.addHandler(handler)

# Environment variables
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
SUBJECT = "task.snyk.request"

async def run_security_scan(task_payload: dict) -> dict:
    """
    Executes a security dependency scan (e.g., using Snyk or Trivy).
    Expects payload fields:
      - target: str (image or project directory)
    Returns status, logs, and any vulnerability summary.
    """
    target = task_payload.get("target")
    tool = task_payload.get("tool", "snyk")
    if tool == "trivy":
        cmd = ["trivy", "image", target, "--format", "json"]
    else:
        # default to Snyk container scan
        cmd = ["snyk", "container", "test", target, "--json"]
    global_logger.info(f"Running security scan: {' '.join(cmd)}")

    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True)
    stdout, _ = proc.communicate()
    return_code = proc.returncode
    status = "pass" if return_code == 0 else "fail"

    # Attempt to parse JSON output for summary
    summary = {}
    try:
        report = json.loads(stdout)
        summary = report.get("vulnerabilities") or report.get("issues") or []
    except json.JSONDecodeError:
        global_logger.warning("Could not parse security scan JSON output.")

    return {"status": status, "logs": stdout, "summary": summary}

async def message_handler(msg):
    try:
        data = json.loads(msg.data.decode())
        run_id = data.get("runId")
        task_id = data.get("taskId")
        payload = data.get("payload", {})
        global_logger.info(f"Received security scan request for task {task_id}")

        result = await run_security_scan(payload)
        response = {
            "runId": run_id,
            "taskId": task_id,
            "status": result["status"],
            "output": {"logs": result["logs"], "summary": result.get("summary", [])}
        }

        await msg.respond(json.dumps(response).encode())
        global_logger.info(f"Published security response for task {task_id} (status={result['status']})")
    except Exception as e:
        global_logger.error(f"Error handling security request: {e}")

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
        global_logger.info("Security agent shutting down...")