# orchestrator/bus.py

import asyncio
import json
import uuid
import yaml
from nats.aio.client import Client as NATS
from orchestrator.graph_tracer import GraphTracer

class NATSPubSub:
    """
    Wrapper around NATS for publishing and subscribing workflow events,
    dispatching tasks, handling runs, and applying auto-fix patches.
    """

    def __init__(self, nats: NATS, tracer: GraphTracer):
        self._nc = nats
        self._tracer = tracer

    async def subscribe(self, subject: str, callback):
        """
        Subscribe to a NATS subject and bind the given async callback.
        """
        sub = await self._nc.subscribe(subject)
        asyncio.create_task(self._listener(sub, callback))
        return sub

    async def _listener(self, subscription, callback):
        async for msg in subscription.messages:
            await callback(msg)

    async def publish(self, subject: str, payload: dict):
        """
        Publish a JSON payload to a NATS subject and flush the connection.
        """
        data = json.dumps(payload).encode()
        await self._nc.publish(subject, data)
        await self._nc.flush()

    async def start_run(self, workflow_id: str, spec: dict, overrides: dict) -> str:
        """
        Kick off a new workflow run. Returns generated run_id.
        Persists run node in Neo4j and publishes plan request.
        """
        run_id = str(uuid.uuid4())
        self._tracer.create_run_node(run_id, workflow_id, spec, overrides)

        # Send planning request
        plan_payload = {
            "text": spec.get("description", f"Run workflow {workflow_id}"),
            "workflowId": workflow_id,
            "runId": run_id,
            "replyTo": "workflow.plan.response"
        }
        await self.publish("workflow.plan.request", plan_payload)
        return run_id

    async def dispatch_tasks(self, run_id: str, dag: dict):
        """
        Given a DAG from planner, create task nodes and publish each to its agent.
        """
        for task in dag.get("tasks", []):
            task_id = task["id"]
            self._tracer.create_task_node(run_id, task_id, task)

            subject = f"task.{task['type']}.request"
            task_payload = {
                "runId": run_id,
                "taskId": task_id,
                "payload": task
            }
            await self.publish(subject, task_payload)

    async def apply_patch_and_retry(self, run_id: str, patch: dict):
        """
        Apply auto-fix patch for a failed task, update DAG in tracer,
        then re-dispatch the corrected task(s).
        """
        task_id = patch.get("taskId")
        updates = patch.get("patch", {})

        self._tracer.record_patch(run_id, task_id, updates)
        corrected_tasks = self._tracer.apply_patch(run_id, task_id, updates)

        for task in corrected_tasks:
            subject = f"task.{task['type']}.request"
            retry_payload = {
                "runId": run_id,
                "taskId": task["id"],
                "payload": task
            }
            await self.publish(subject, retry_payload)
