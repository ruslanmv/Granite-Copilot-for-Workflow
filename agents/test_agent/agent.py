import os
import sys
import asyncio
import json
import logging
from nats.aio.client import Client as NATS

# Configure logging
global_logger = logging.getLogger("test_agent")
global_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
global_logger.addHandler(handler)

# Environment variables
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
SUBJECT = "task.pytest.request"

async def run_tests(task_payload: dict) -> dict:
    """
    Runs pytest on the specified directory or file.
    Expects payload fields:
      - path: str (path to test directory or file)
    Returns status and test summary.
    """
    path = task_payload.get("path", "./")
    cmd = ["pytest", path, "--json-report", "--json-report-file=report.json"]
    global_logger.info(f"Running tests: {' '.join(cmd)}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    logs = stdout.decode()
    return_code = proc.returncode
    status = "pass" if return_code == 0 else "fail"

    # Parse JSON report if exists
    summary = {}
    try:
        with open("report.json") as f:
            report = json.load(f)
            summary = {
                "total": report.get("summary", {}).get("total", 0),
                "passed": report.get("summary", {}).get("passed", 0),
                "failed": report.get("summary", {}).get("failed", 0),
                "skipped": report.get("summary", {}).get("skipped", 0),
            }
    except Exception:
        global_logger.warning("Could not parse pytest JSON report.")

    return {"status": status, "logs": logs, "summary": summary}

async def message_handler(msg):
    try:
        data = json.loads(msg.data.decode())
        run_id = data.get("runId")
        task_id = data.get("taskId")
        payload = data.get("payload", {})
        global_logger.info(f"Received test request for task {task_id}")

        result = await run_tests(payload)
        response = {
            "runId": run_id,
            "taskId": task_id,
            "status": result["status"],
            "output": {"logs": result["logs"], "summary": result.get("summary", {})}
        }

        await msg.respond(json.dumps(response).encode())
        global_logger.info(f"Published test response for task {task_id} (status={result['status']})")
    except Exception as e:
        global_logger.error(f"Error handling test request: {e}")

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
        global_logger.info("Test agent shutting down...")