# agents/observer_agent/agent.py

import os
import json
import asyncio
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

class ObserverAgent:
    """
    Listens on 'workflow.logs.stream' NATS subject,
    captures logs and metrics, and posts notifications (e.g., Slack).
    """

    SUBJECT = "workflow.logs.stream"

    def __init__(self, nc: NATS):
        self.nc = nc
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if not self.slack_webhook:
            raise ValueError("SLACK_WEBHOOK_URL is missing or empty.")

    async def run(self):
        sub = await self.nc.subscribe(self.SUBJECT)
        async for msg in sub.messages:
            try:
                entry = json.loads(msg.data.decode())
                await self.handle(entry)
            except Exception as e:
                print(f"[ObserverAgent] Failed to process log entry: {e}")

    async def handle(self, entry: dict):
        # Print to console (could stream to Prometheus, etc.)
        ts = entry.get("timestamp")
        lvl = entry.get("level")
        msg = entry.get("message")
        log_line = f"[{ts}] [{lvl}] {msg}"
        print(log_line)

        # Notify Slack on errors or warnings
        if lvl in ("ERROR", "WARN"):
            await self.post_to_slack(entry)

    async def post_to_slack(self, entry: dict):
        import aiohttp
        text = f"*{entry.get('level')}* at {entry.get('timestamp')}: {entry.get('message')}"
        payload = {"text": text}
        async with aiohttp.ClientSession() as session:
            async with session.post(self.slack_webhook, json=payload) as resp:
                if resp.status != 200:
                    print(f"[ObserverAgent] Slack webhook failed: {resp.status}")

if __name__ == "__main__":
    async def main():
        nc = NATS()
        await nc.connect(servers=[os.getenv("NATS_URL")])
        agent = ObserverAgent(nc)
        await agent.run()

    asyncio.run(main())
