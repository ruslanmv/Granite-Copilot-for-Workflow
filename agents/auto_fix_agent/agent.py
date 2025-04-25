import os
import json
import asyncio
from abc import ABC, abstractmethod
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai import Credentials

# Load environment variables
API_KEY = os.getenv("WATSONX_APIKEY")
URL     = os.getenv("WATSONX_URL")
PROJECT = os.getenv("PROJECT_ID")

if not all([API_KEY, URL, PROJECT]):
    raise ValueError("Missing one of WATSONX_APIKEY, WATSONX_URL, PROJECT_ID")

# Initialize LLM client
creds = Credentials(url=URL, api_key=API_KEY)
MODEL = ModelInference(model_id="ibm/granite-13b-instruct-v2",
                       credentials=creds,
                       project_id=PROJECT)

class BaseAgent(ABC):
    @abstractmethod
    async def handle(self, msg: dict) -> dict:
        ...

class AutoFixAgent(BaseAgent):
    """
    Listens on 'workflow.autofix.request' for failed tasks,
    prompts Granite to generate a patch, and replies with 'workflow.autofix.response'.
    """

    SUBJECT_REQUEST  = "workflow.autofix.request"
    SUBJECT_RESPONSE = "workflow.autofix.response"

    def __init__(self, nc):
        self.nc = nc

    async def run(self):
        sub = await self.nc.subscribe(self.SUBJECT_REQUEST)
        async for m in sub.messages:
            payload = json.loads(m.data.decode())
            response = await self.handle(payload)
            await self.nc.publish(
                self.SUBJECT_RESPONSE,
                json.dumps(response).encode()
            )

    async def handle(self, msg: dict) -> dict:
        run_id  = msg.get("runId")
        task_id = msg.get("taskId")
        failure = msg.get("output", {})
        prompt  = (
            f"The task '{task_id}' in run '{run_id}' failed with output:\n"
            f"{json.dumps(failure, indent=2)}\n\n"
            "Generate a JSON patch with key 'patch' to correct the task parameters or code. "
            "Return: {\"taskId\": ..., \"patch\": {...}}"
        )

        result = MODEL.generate_text(prompt=prompt, params={
            "decoding_method": "greedy",
            "max_new_tokens": 200
        })

        # Attempt to parse returned JSON
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Fallback minimal patch
            return {"taskId": task_id, "patch": {}}

if __name__ == "__main__":
    import asyncio
    from nats.aio.client import Client as NATS

    async def main():
        nc = NATS()
        await nc.connect(servers=[os.getenv("NATS_URL")])
        agent = AutoFixAgent(nc)
        await agent.run()

    asyncio.run(main())
