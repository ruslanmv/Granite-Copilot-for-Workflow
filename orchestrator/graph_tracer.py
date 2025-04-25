from typing import Any, Dict, List, Optional
import os
import yaml
from neo4j import GraphDatabase, BoltDriver

class GraphTracer:
    """
    Persists workflows, runs, tasks, and patches in Neo4j for provenance and audit.
    """

    def __init__(self, uri: str, user: str, pwd: str):
        self._driver: BoltDriver = GraphDatabase.driver(uri, auth=(user, pwd))

    def close(self):
        self._driver.close()

    def create_workflow_node(self, workflow_id: str, spec: Dict[str, Any]):
        """
        Create or update a Workflow node with its YAML spec.
        """
        spec_yaml = yaml.safe_dump(spec)
        with self._driver.session() as ses:
            ses.run(
                """
                MERGE (w:Workflow {id: $workflow_id})
                SET w.spec = $spec_yaml, w.name = $workflow_id
                """,
                workflow_id=workflow_id,
                spec_yaml=spec_yaml
            )

    def list_workflows(self) -> List[Dict[str, str]]:
        """
        Return list of workflows with id, name, and schedule.
        """
        with self._driver.session() as ses:
            result = ses.run(
                """
                MATCH (w:Workflow)
                RETURN w.id AS workflowId, w.name AS name, w.spec AS spec_yaml
                """
            )
            out = []
            for rec in result:
                spec = yaml.safe_load(rec["spec_yaml"])
                out.append({
                    "workflowId": rec["workflowId"],
                    "name": rec["name"],
                    "schedule": spec.get("schedule", "")
                })
            return out

    def get_workflow_spec(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the full YAML spec for given workflow.
        """
        with self._driver.session() as ses:
            rec = ses.run(
                """
                MATCH (w:Workflow {id: $workflow_id})
                RETURN w.spec AS spec_yaml
                """,
                workflow_id=workflow_id
            ).single()
            if not rec:
                return None
            return yaml.safe_load(rec["spec_yaml"])

    def create_run_node(
        self, run_id: str, workflow_id: str, spec: Dict[str, Any], overrides: Dict[str, Any]
    ):
        """
        Record a new Run node linked to its Workflow.
        """
        spec_yaml = yaml.safe_dump(spec)
        overrides_yaml = yaml.safe_dump(overrides)
        with self._driver.session() as ses:
            ses.run(
                """
                MATCH (w:Workflow {id: $workflow_id})
                MERGE (r:Run {id: $run_id})
                SET r.startedAt = datetime(), r.status = 'running',
                    r.spec = $spec_yaml, r.overrides = $overrides_yaml
                MERGE (w)-[:HAS_RUN]->(r)
                """,
                run_id=run_id,
                workflow_id=workflow_id,
                spec_yaml=spec_yaml,
                overrides_yaml=overrides_yaml
            )

    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch Run node and its Task statuses.
        """
        with self._driver.session() as ses:
            rec = ses.run(
                """
                MATCH (r:Run {id: $run_id})
                OPTIONAL MATCH (r)-[:EXECUTED]->(t:Task)
                RETURN r.id AS runId, r.status AS status,
                       r.startedAt AS startedAt, r.completedAt AS completedAt,
                       collect({
                         taskId: t.id,
                         type: t.type,
                         status: t.status,
                         startedAt: t.startedAt,
                         completedAt: t.completedAt
                       }) AS tasks
                """,
                run_id=run_id
            ).single()
            if not rec:
                return None
            return {
                "runId": rec["runId"],
                "status": rec["status"],
                "startedAt": rec["startedAt"],
                "completedAt": rec["completedAt"],
                "tasks": rec["tasks"]
            }

    def create_task_node(self, run_id: str, task_id: str, task_payload: Dict[str, Any]):
        """
        Record a Task node for a given Run.
        """
        payload_yaml = yaml.safe_dump(task_payload)
        with self._driver.session() as ses:
            ses.run(
                """
                MATCH (r:Run {id: $run_id})
                MERGE (t:Task {id: $task_id})
                SET t.type = $type, t.payload = $payload_yaml,
                    t.status = 'pending'
                MERGE (r)-[:EXECUTED]->(t)
                """,
                run_id=run_id,
                task_id=task_id,
                type=task_payload.get("type", ""),
                payload_yaml=payload_yaml
            )

    def record_task_result(
        self, run_id: str, task_id: str, status: str, output: Any
    ):
        """
        Update Task node status and output, mark Run completed if all done.
        """
        output_yaml = yaml.safe_dump(output)
        with self._driver.session() as ses:
            ses.run(
                """
                MATCH (t:Task {id: $task_id})<-[:EXECUTED]-(r:Run {id: $run_id})
                SET t.status = $status,
                    t.output = $output_yaml,
                    t.completedAt = datetime()
                """,
                run_id=run_id,
                task_id=task_id,
                status=status,
                output_yaml=output_yaml
            )
            # Check if all tasks done
            res = ses.run(
                """
                MATCH (r:Run {id: $run_id})-[:EXECUTED]->(t:Task)
                WITH r, collect(t.status) AS stats
                WHERE NONE(s IN stats WHERE s = 'pending' OR s = 'running')
                RETURN ALL(s IN stats WHERE s = 'pass') AS allPassed
                """,
                run_id=run_id
            ).single()
            if res:
                all_passed = res["allPassed"]
                new_status = "success" if all_passed else "failed"
                ses.run(
                    """
                    MATCH (r:Run {id: $run_id})
                    SET r.status = $new_status, r.completedAt = datetime()
                    """,
                    run_id=run_id,
                    new_status=new_status
                )

    def record_patch(self, run_id: str, task_id: str, updates: Dict[str, Any]):
        """
        Record that an AutoFix patch was applied to a Task.
        """
        updates_yaml = yaml.safe_dump(updates)
        with self._driver.session() as ses:
            ses.run(
                """
                MATCH (t:Task {id: $task_id})<-[:EXECUTED]-(r:Run {id: $run_id})
                MERGE (p:Patch {id: randomUUID()})
                SET p.timestamp = datetime(), p.updates = $updates_yaml
                MERGE (r)-[:HAS_PATCH]->(p)
                MERGE (p)-[:PATCH_OF]->(t)
                """,
                run_id=run_id,
                task_id=task_id,
                updates_yaml=updates_yaml
            )

    def apply_patch(self, run_id: str, task_id: str, updates: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Modify in-memory DAG spec for the run and return corrected task(s).
        """
        # Load stored spec, apply patch, and re-persist. Simplest: rewrite node properties
        with self._driver.session() as ses:
            rec = ses.run(
                """
                MATCH (r:Run {id: $run_id})
                RETURN r.spec AS spec_yaml
                """,
                run_id=run_id
            ).single()
            spec = yaml.safe_load(rec["spec_yaml"])
            # Find and update the specific task in spec
            for task in spec.get("tasks", []):
                if task["id"] == task_id:
                    task.update(updates)
            # Save updated spec back
            updated_yaml = yaml.safe_dump(spec)
            ses.run(
                """
                MATCH (r:Run {id: $run_id})
                SET r.spec = $updated_yaml
                """,
                run_id=run_id,
                updated_yaml=updated_yaml
            )
            return spec.get("tasks", [])
# at bottom of graph_tracer.py
    def __del__(self):
        self.close()