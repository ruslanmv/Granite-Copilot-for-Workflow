# agents/doc_agent/agent.py
import os
import json
import asyncio
from nats.aio.client import Client as NATS
from orchestrator.llm_client import LLMClient

class DocAgent:
    """
    Agent that generates documentation or release notes using Granite LLM.
    Listens on subject 'task.llm-doc.request'.
    """
    subject = "task.llm-doc.request"

    def __init__(self, nats_url: str):
        self.nc = NATS()
        self.nats_url = nats_url
        self.llm = LLMClient()

    async def start(self):
        # Connect to NATS and subscribe
        await self.nc.connect(servers=[self.nats_url])
        sub = await self.nc.subscribe(self.subject)
        print(f"[DocAgent] Listening on {self.subject}")
        async for msg in sub.messages:
            asyncio.create_task(self.handle(msg))

    async def handle(self, msg):
        try:
            data = json.loads(msg.data.decode())
            run_id = data.get("runId")
            task_id = data.get("taskId")
            payload = data.get("payload", {})
            template_path = payload.get("template")
            source = payload.get("data_source")

            # Load template
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template not found: {template_path}")
            with open(template_path) as f:
                template = f.read()

            # Fetch data for template (e.g., GitHub PRs)
            # For demo, we stub it as an empty dict
            context = {"pr_list": []}

            # Render prompt
            prompt = template.format(**context)

            # Call LLM to generate docs
            doc_text = self.llm.generate_text(prompt)

            # Publish response
            response = {
                "runId": run_id,
                "taskId": task_id,
                "status": "pass",
                "output": {"doc": doc_text}
            }
            reply_subj = f"task.llm-doc.response"
            await self.nc.publish(reply_subj, json.dumps(response).encode())
            print(f"[DocAgent] Published to {reply_subj}")
        except Exception as e:
            err = str(e)
            response = {
                "runId": data.get("runId"),
                "taskId": data.get("taskId"),
                "status": "fail",
                "errors": [err]
            }
            reply_subj = f"task.llm-doc.response"
            await self.nc.publish(reply_subj, json.dumps(response).encode())
            print(f"[DocAgent] Error: {err}")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    nats_url = os.getenv("NATS_URL", "nats://nats:4222")
    agent = DocAgent(nats_url)
    asyncio.run(agent.start())
